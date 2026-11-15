#!/usr/bin/env python3
"""AI-DDD の工程の関門を守らせるフック（Claude Code と Codex で共通）。

プロジェクトでは `.ai-ddd/hooks/ai_ddd_hook.py` に置き、次のように呼ぶ。

    python3 .ai-ddd/hooks/ai_ddd_hook.py <event>

<event> は user-prompt-submit / pre-tool-use / session-start / stop のどれか。
入力はフックの仕様どおり stdin の JSON で受け取る。

段階は `.ai-ddd/phase` に 1 語で記録する。
    intake … ① 要求の整理の間。要求の記録以外の変更を止める
    work   … 合図「以上」のあと。決まった流れで進める
段階を切り替えるのはこのフックだけで、AI 自身には書き換えさせない。

止まる場所（A・B・C）で AI が「はい／いいえ」で聞くときは、AI が `.ai-ddd/awaiting` に
印（例: "B #42"）を置く。印があるときにユーザーが「はい」だけを答えたら、フックが段階を work にする
（合図「以上」を重ねて求めない。#42）。印がないときの「はい」では段階を変えない。

設定は `.ai-ddd/hooks.json`（なければ下の DEFAULT_CONFIG）。
"""
import json
import os
import re
import shlex
import subprocess
import sys

DEFAULT_CONFIG = {
    # session: 新しいセッション・/clear・「まって」で intake、「以上」で work。work は次の切り替えまで続く
    # strict : ユーザーの発言のたびに intake に戻る。「以上」を含む発言のときだけ work にする
    "mode": "session",
    "start_words": ["以上"],
    "stop_words": ["まって", "待って"],
    # 止まる場所の印（.ai-ddd/awaiting）があるとき、発言全体がこれなら次の工程に進める
    "approve_words": ["はい", "ok", "お願いします", "おねがいします", "進めて", "進めてください", "yes"],
    # intake の間も編集してよい場所（リポジトリ直下からの相対パスの先頭）
    "intake_allowed_paths": [
        "docs/requests/",
        "docs/progress-status.md",
        "docs/improvement-log.md",
    ],
}

PHASE_FILE = os.path.join(".ai-ddd", "phase")
AWAITING_FILE = os.path.join(".ai-ddd", "awaiting")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}
# intake の間に止める、変更を伴うシェル操作
MUTATING_SHELL = re.compile(
    r"(^|[;&|]\s*)(git\s+(push|merge|rebase|reset|checkout|switch|restore|stash|clean|rm|mv|apply|am|cherry-pick|revert)\b"
    r"|rm\s|mv\s|cp\s|mkdir\s|touch\s|sed\s+-i|perl\s+-pi|tee\s|truncate\s|chmod\s|npm\s+(install|i)\b|composer\s+(install|require|update)\b"
    r"|php\s+artisan\s+(migrate|db:)|docker(-compose|\s+compose)?\s+.*\b(down|rm|exec)\b)"
)
REDIRECT = re.compile(r"(?<![<>&0-9])>{1,2}\s*([^\s&|;]+)")
PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.M)
GIT_COMMIT = re.compile(r"(^|[;&|]\s*)git\s+commit\b")
GIT_ADD = re.compile(r"(?:^|[;&|]\s*)git\s+add\s+([^;&|]*)")


def repo_root(cwd):
    # Claude Code はプロジェクトの場所を渡す。作業場所がサブモジュールに移っていても段階のファイルを取り違えない
    # （online-study-system #58 で入れた直しを雛形に取り込んだ。2026-11-14）
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir and os.path.isdir(project_dir):
        return project_dir
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except Exception:
        return cwd


def load_config(root):
    cfg = dict(DEFAULT_CONFIG)
    path = os.path.join(root, ".ai-ddd", "hooks.json")
    try:
        with open(path, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except FileNotFoundError:
        pass
    return cfg


def read_phase(root):
    try:
        with open(os.path.join(root, PHASE_FILE), encoding="utf-8") as f:
            return f.read().strip() or "intake"
    except FileNotFoundError:
        return "intake"


def write_phase(root, phase):
    os.makedirs(os.path.join(root, ".ai-ddd"), exist_ok=True)
    with open(os.path.join(root, PHASE_FILE), "w", encoding="utf-8") as f:
        f.write(phase + "\n")


def has_awaiting(root):
    return os.path.exists(os.path.join(root, AWAITING_FILE))


def clear_awaiting(root):
    try:
        os.remove(os.path.join(root, AWAITING_FILE))
    except FileNotFoundError:
        pass


def rel(root, path):
    if not path:
        return ""
    p = os.path.normpath(path if os.path.isabs(path) else os.path.join(root, path))
    r = os.path.relpath(p, root)
    return r.replace(os.sep, "/")


def allowed(cfg, relpath):
    if relpath == AWAITING_FILE.replace(os.sep, "/"):
        return True  # 止まる場所の印は、要求の整理中でも AI が置いてよい
    return any(relpath == a.rstrip("/") or relpath.startswith(a) for a in cfg["intake_allowed_paths"])


PHASE_PATH = re.compile(r"^[^\s'\"]*\.ai-ddd/phase$")


def is_phase_path(token):
    """段階のファイルを指すパスか。前にフォルダや変数（$S/ など）があってもよい。空白を含む文字列（sed の式など）は違う。"""
    return bool(PHASE_PATH.match(token.strip("'\"")))


def writes_phase_file(cmd, root, cwd):
    """シェルのコマンドが段階のファイルに書き込むかどうか。読むだけなら False（改善の記録 No.18・21）。

    どのプロジェクトの段階のファイルでも、書き込み先が段階のファイルなら止める。
    段階のファイルの名前が、書き込み先ではない文字列（sed の式、grep の検索語など）に出てくるだけなら止めない。
    """
    if ".ai-ddd/phase" not in (cmd or ""):
        return False
    for target in REDIRECT.findall(cmd):
        if is_phase_path(target):
            return True
    for part in re.split(r"[;&|]+", cmd):
        if ".ai-ddd/phase" not in part or not MUTATING_SHELL.search(part.strip()):
            continue
        try:
            tokens = shlex.split(part)
        except ValueError:
            tokens = part.split()
        if any(is_phase_path(t) for t in tokens[1:]):
            return True
    return False


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))
    return 0


INTAKE_REASON = (
    "いまは ① 要求の整理の途中です（AI-DDD）。要求の記録（{paths}）以外の変更はできません。"
    "ユーザーの合図「以上」を待ってください。"
)


def staged_files(root):
    try:
        out = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=root,
                             capture_output=True, text=True, check=True)
        return [l for l in out.stdout.splitlines() if l.strip()]
    except Exception:
        return []


def on_pre_tool_use(data, root, cfg):
    tool = data.get("tool_name", "")
    tin = data.get("tool_input") or {}
    phase = read_phase(root)
    paths = "、".join(cfg["intake_allowed_paths"])

    if tool in EDIT_TOOLS:
        target = rel(root, tin.get("file_path") or tin.get("notebook_path") or "")
        if target == PHASE_FILE.replace(os.sep, "/"):
            return deny("段階のファイル（.ai-ddd/phase）は、フックだけが切り替えます。AI は書き換えないでください。")
        if phase == "intake" and not allowed(cfg, target):
            return deny(INTAKE_REASON.format(paths=paths))
        return 0

    if tool == "apply_patch":
        patch = tin.get("command") or tin.get("input") or ""
        files = [rel(root, f.strip()) for f in PATCH_FILE.findall(patch)]
        if any(f == ".ai-ddd/phase" for f in files):
            return deny("段階のファイル（.ai-ddd/phase）は、フックだけが切り替えます。AI は書き換えないでください。")
        if phase == "intake" and any(not allowed(cfg, f) for f in files):
            return deny(INTAKE_REASON.format(paths=paths))
        return 0

    if tool in SHELL_TOOLS:
        cmd = tin.get("command") or ""
        if writes_phase_file(cmd, root, data.get("cwd") or root):
            return deny("段階のファイル（.ai-ddd/phase）は、フックだけが切り替えます。AI は書き換えないでください。")
        if phase != "intake":
            return 0
        cwd = data.get("cwd") or root
        for args in GIT_ADD.findall(cmd):
            targets = [a for a in args.split() if not a.startswith("-") or a in ("-A", "--all", "-u")]
            if not targets or any(a in ("-A", "--all", "-u", ".", "*") for a in targets):
                bad = [l[3:] for l in uncommitted(root) if not allowed(cfg, l[3:].strip('"'))]
            else:
                bad = [a for a in targets if not allowed(cfg, rel(root, os.path.join(cwd, a)))]
            if bad:
                return deny(INTAKE_REASON.format(paths=paths) + " 追加しようとしている対象: " + "、".join(bad[:5]))
        if GIT_COMMIT.search(cmd):
            bad = [f for f in staged_files(root) if not allowed(cfg, f)]
            if bad:
                return deny(INTAKE_REASON.format(paths=paths) + " コミットしようとしている対象: " + "、".join(bad[:5]))
            return 0
        if MUTATING_SHELL.search(cmd):
            return deny(INTAKE_REASON.format(paths=paths))
        for target in REDIRECT.findall(cmd):
            if target.startswith("/dev/"):
                continue
            if not allowed(cfg, rel(root, os.path.join(cwd, target))):
                return deny(INTAKE_REASON.format(paths=paths))
        return 0
    return 0


def matches(text, words):
    t = text.strip()
    return any(t == w or t.endswith(w) for w in words)


def contains(text, words):
    return any(w in text for w in words)


def is_exactly(text, words):
    """発言全体が合図の言葉そのもの（前後の空白・句読点・記号を除く）かどうか。"""
    t = re.sub(r"[\s、。！!？?…・ー〜~]+", "", text).lower()
    return t in [w.lower() for w in words]


def on_user_prompt_submit(data, root, cfg):
    prompt = (data.get("prompt") or "").strip()
    phase = read_phase(root)
    awaiting = has_awaiting(root)
    clear_awaiting(root)  # 印は 1 回の返事で使い切る。質問がそれたら AI が聞き直すときに置き直す
    if is_exactly(prompt, cfg["stop_words"]):
        write_phase(root, "intake")
        print("【AI-DDD】ユーザーが「まって」と伝えた。今の作業を止め、① 要求の整理に戻る。要求の記録・回答・質問だけをし、合図「以上」を待つ。")
        return 0
    if (cfg["mode"] == "strict" and contains(prompt, cfg["start_words"])) or \
       (cfg["mode"] != "strict" and matches(prompt, cfg["start_words"])):
        write_phase(root, "work")
        print("【AI-DDD】合図「以上」を受けた。要求の一覧を確定し、決まった流れ（② 要件抽出 〜）で止まらずに進める。止まるのは A・B・C だけ。")
        return 0
    if awaiting and is_exactly(prompt, cfg.get("approve_words", DEFAULT_CONFIG["approve_words"])):
        write_phase(root, "work")
        print("【AI-DDD】止まる場所の承認（「はい」）を受けた。合図「以上」は要らない。決まった流れで次の工程に進める。")
        return 0
    if cfg["mode"] == "strict":
        write_phase(root, "intake")
        phase = "intake"
    if phase == "intake":
        print("【AI-DDD】いまは ① 要求の整理の途中。この発言を要求として記録し、回答・質問だけをする。実装や変更は合図「以上」まで始めない。")
    return 0


def on_session_start(data, root, cfg):
    source = data.get("source", "")
    if source in ("startup", "clear"):
        clear_awaiting(root)  # 前のセッションの質問は無効。AI は進捗を読んで聞き直す
    if source in ("startup", "clear") and cfg["mode"] in ("session", "strict"):
        write_phase(root, "intake")
    phase = read_phase(root)
    label = "① 要求の整理の途中（合図「以上」まで実装や変更を始めない）" if phase == "intake" else "合図「以上」のあと（決まった流れで進める）"
    print(
        "【AI-DDD】このプロジェクトは AI-DDD で進める。ルールの正本は AGENTS.md。\n"
        f"- 今の段階: {label}\n"
        "- 止まるのは A（要件の判断）・B（設計と課題分割の確認）・C（テスト結果の確認）だけ。「まって」で止まる。\n"
        "- 止まる場所で聞くときは、.ai-ddd/awaiting に印（例: B #42）を置く。ユーザーの「はい」だけで次へ進める。\n"
        "- 作業を続ける前に docs/progress-status.md と進行中の Issue の docs を読み、現在地を取り戻す。\n"
        "- 会話の中だけで決まったことがあれば docs に書く。作業のまとまりごとにコミットする。"
    )
    return 0


def uncommitted(root):
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=root,
                             capture_output=True, text=True, check=True)
        return [l for l in out.stdout.splitlines() if l.strip() and not l.endswith((".ai-ddd/phase", ".ai-ddd/awaiting"))]
    except Exception:
        return []


def on_stop(data, root, cfg):
    if data.get("stop_hook_active"):
        return 0
    files = uncommitted(root)
    if not files:
        return 0
    sample = "、".join(l[3:] for l in files[:5])
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"【AI-DDD】未コミットの変更が {len(files)} 件あります（例: {sample}）。"
            "中身を確かめて、作業のまとまりごとにコミットしてください。残す必要があるものは、理由を docs に書いてください。"
        ),
    }, ensure_ascii=False))
    return 0


HANDLERS = {
    "pre-tool-use": on_pre_tool_use,
    "user-prompt-submit": on_user_prompt_submit,
    "session-start": on_session_start,
    "stop": on_stop,
}


def main(argv, stdin=sys.stdin):
    if len(argv) < 2 or argv[1] not in HANDLERS:
        print("usage: ai_ddd_hook.py {" + "|".join(HANDLERS) + "}", file=sys.stderr)
        return 1
    try:
        data = json.load(stdin)
    except Exception:
        data = {}
    root = repo_root(data.get("cwd") or os.getcwd())
    cfg = load_config(root)
    return HANDLERS[argv[1]](data, root, cfg)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
