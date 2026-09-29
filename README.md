<div align="center">

<h1>Agent Kickstart</h1>

<p><strong>A guided first project for people new to Claude Code.</strong></p>

<p>Agent Kickstart is developed by <a href="https://hermes-labs.ai">Hermes Labs</a>.</p>

<p>Hermes Labs is an agentic infrastructure company building the reliability layer for autonomous systems.</p>

[![CI](https://github.com/hermes-labs-ai/agent-kickstart/actions/workflows/ci.yml/badge.svg)](https://github.com/hermes-labs-ai/agent-kickstart/actions/workflows/ci.yml)

</div>

Agent Kickstart takes you from an empty folder to a concrete starting point: a
family recipe page, a decision map, a small local helper, or another project
shaped around what you actually care about. It asks a few questions, separates
what you said from what it is only inferring, proposes specific projects, and
begins the one you choose with you.

**You do not need to know how to code or already be comfortable with a
terminal.** You can ramble, use dictation, make typos, change your mind, or
reject every suggestion. Kickstart gives you the one terminal line you need to
copy and paste.

## Start here

You need [Claude Code](https://code.claude.com/docs/en/overview) and Node.js 18 or newer.

Open Claude Code in an empty folder and paste this sentence:

> Install Agent Kickstart from https://github.com/hermes-labs-ai/agent-kickstart and walk me through it — I'm new to this.

That is enough. The repository carries its own instructions for the installing agent
(`AGENTS.md`): it will briefly explain what Kickstart is before downloading anything, keep
everything inside your folder, run the installer, and hand you **one copy-paste line** that
starts Kickstart. On a Mac the installer even puts that line on your clipboard for you.

The line looks like this (with your real folder path):

```text
cd -- /path/to/your/folder && claude "/kickstart"
```

Paste it into your terminal (type `/exit` first if you're still inside Claude Code) and
Kickstart begins. The same line works any time you come back — nothing to memorize. If a
workspace trust screen appears, confirm it names your folder, review the project
permissions, and choose **Yes, I trust this folder**. The one close-and-reopen is how Claude
Code discovers newly installed project commands — part of installation, not an error.

## What your first session feels like

Agent Kickstart will:

1. ask how carefully it should handle actions in the folder;
2. invite you to describe yourself in your own words;
3. ask two or three follow-up questions based on what you actually said;
4. show what it heard as facts and what it is only tentatively inferring;
5. offer several specific things you could make, explore, understand, or improve;
6. let you choose, combine, change, or reject those ideas; and
7. begin one real thing with you immediately.

The choices appear in Claude Code's built-in selector when it is available. A free-text path is always available, so the menu never limits what you can ask for.

After that, ordinary language is the interface. Try things like:

> Make the second idea more playful.

> None of those. Surprise me in a different direction.

> I feel overwhelmed. Give me one tiny next step.

> Explain what you just changed.

## Stop, resume, or correct it

Leave guided mode without deleting anything:

```text
/leave-kickstart
```

You can also say “turn this off” or “go back to normal Claude.” Starting a fresh Claude Code session gives you the cleanest normal context.

If onboarding is interrupted, run `/kickstart` again. It resumes from the saved stage.

Your portrait is plain Markdown in `agent-kickstart/state/user-portrait.md`. At any time, say:

- “Show me what you think you know about me.”
- “That is wrong—update my portrait.”
- “Delete my portrait.”
- “Use simpler guidance.”
- “Let me take more control.”

Deletion and reset require confirmation. Both delete the private extracted-history corpus;
reset preserves everything in `agent-kickstart/creations/`.

## Safety and privacy

Agent Kickstart stays inside this project by default. It does not change your global Claude settings, inspect unrelated personal files, read common credential files, bypass permissions, or publish anything for you. Consequential actions still require an explanation and your approval.

Your portrait, interview notes, progress state, and creations remain local files in the project. After the safety stage, the optional existing-history fast lane performs a local counts-only eligibility scan: it parses candidate transcript messages but writes nothing and returns no content. It extracts eligible transcripts and memory into a private corpus only after an engine-recorded choice; choosing the interview mechanically blocks extraction. That corpus stays in the project and is deleted with either “Delete my portrait” or reset. These state files are ignored by Git so they are not accidentally committed. You can read, edit, or delete them.

This is defense in depth, not an operating-system sandbox. Always read Claude Code's permission prompts before approving them.

## Preview before you install

Before anything is written, you can see exactly what an installation would do:

```sh
agent-kickstart plan --target ./my-first-project
```

`plan` writes nothing anywhere. It lists every file Kickstart would manage and
whether each one would be created, is already identical, or conflicts with a
file you already have; to tell those apart, it compares the bytes of the
managed files already present against the versions it would install. On the
JavaScript route it also checks whether the target folder is empty, which means
listing that folder's entries — it does not open them. It reports whether
Claude Code and Node.js are present, and prints the exact commands you would
run, including the one-line start command — except when a finding means those
commands would fail, in which case it withholds them and says so.

With `--json`, the record carries a `gitSha` field describing the checkout
Agent Kickstart is running from, read with `git rev-parse HEAD` and `git status
--porcelain`. If you installed into a Python environment that lives inside one
of your own Git repositories, that is the repository whose commit and
clean-or-dirty state the field reports.

`agent-kickstart install --dry-run` is the same human-readable preview. Add
`--path javascript` to either preview command to inspect the
repository-and-installer route instead of the Python one. For a
machine-readable result record, use `agent-kickstart plan --json`.

Nothing is installed until you run `agent-kickstart install` yourself.

## Python installation

Install the helper into your current Python environment, then run it inside the
empty folder where you want to begin. Using `python -m` keeps both commands tied
to the same interpreter, which matters if your machine has more than one Python
installed:

```sh
python -m pip install agent-kickstart
python -m agent_kickstart install
```

The helper checks for Claude Code and Node.js, copies the Kickstart harness only
into that project, and prints the correct one-line start command for your
terminal. If you know only one Python is on your PATH, the shorter
`pip install agent-kickstart` and `agent-kickstart install` are equivalent.
To confirm which release you installed, run `python -c "from importlib.metadata import version; print(version('agent-kickstart'))"`.

If you used an earlier version, the `claude-kickstart` command remains available as a
compatibility alias. New installations and documentation use `agent-kickstart`.

If you already downloaded the repository, open a terminal inside it and run:

macOS or Linux:

```sh
bash install.sh
```

Windows PowerShell:

```powershell
.\install.ps1
```

The harness installation is project-local and repeatable. It initializes only
missing state and never overwrites your portrait, history, or creations. The
Python helper itself remains installed in the Python environment where you ran
`pip install`.

To stop using it, run `/leave-kickstart`. Because the harness is self-contained,
you can then archive or remove the repository whenever you no longer need the
local portrait or creations. If you installed the Python helper, remove that
separately with `pip uninstall agent-kickstart`.

## Install from the Hermes Labs plugin marketplace

Agent Kickstart is also listed in the Hermes Labs Claude Code plugin marketplace,
[hermes-labs-ai/claude-plugins](https://github.com/hermes-labs-ai/claude-plugins).
Inside Claude Code, run:

```text
/plugin marketplace add hermes-labs-ai/claude-plugins
/plugin install agent-kickstart@hermes-labs
```

The plugin's entry command is `/agent-kickstart:kickstart`. A plugin install
provides the commands and lifecycle hooks but not Kickstart's project permission
rules (see [Requirements and honest limits](#requirements-and-honest-limits)), so
the project-local installers above remain the recommended path for beginners.

## If something does not work

- **`/kickstart` is not recognized:** type `/exit` and run the exact start line
  printed by the installer. If it still fails, tell Claude: “Verify
  `.claude/commands/kickstart.md` in this folder and repair only this
  project-local installation.”
- **Claude says a required file is missing:** make sure you opened the downloaded `agent-kickstart` folder, then run the installer again. It will explain what is missing without guessing or overwriting files.
- **Node.js is missing or too old:** install Node.js 18 or newer, confirm `node --version` works, and rerun the installer.
- **You see a workspace trust screen:** confirm the folder came from `hermes-labs-ai/agent-kickstart`, review the listed project permissions, and proceed only if you trust it.
- **You stopped halfway through:** reopen the same folder and run `/kickstart`; your pending stage should resume.

If the problem remains, open a [GitHub issue](https://github.com/hermes-labs-ai/agent-kickstart/issues) without including private portrait or session content.

## Requirements and honest limits

- Agent Kickstart is intentionally Claude Code-specific. Its project commands,
  permission settings, lifecycle hooks, native selector, and optional history
  import use Claude Code surfaces. Supporting Codex or another agent requires a
  separate adapter and is not claimed in this release.
- Claude Code 2.1 or newer
- Node.js 18 or newer
- Tested on macOS and Linux with the current Claude Code CLI (2.1.x)
- One close-and-reopen is required after the first installation so Claude Code can discover Kickstart's project command, safety settings, and lifecycle hooks
- The supported installers (`install.sh`, `install.ps1`, `agent-kickstart install`) place `.claude/settings.json`, with Kickstart's permission rules, inside the project. Loading this repository as a Claude Code plugin (entry command `/agent-kickstart:kickstart`) provides the commands and lifecycle hooks, but Claude Code does not apply permission rules from a plugin; for a plugin-only setup, merge the `permissions` block from this repository's `settings.json` into the project's `.claude/settings.json`
- Shell installer exercised end-to-end on Linux in CI (`tests/installer.test.mjs`); it is not exercised on a macOS CI runner. The PowerShell installer is syntax- and logic-checked but has not been run on Windows in this release
- Claude generates the adaptive questions and possibilities at runtime, so exact wording varies
- If Claude Code's native selector is unavailable, Kickstart uses a numbered text fallback
- The thin project-command files use Claude Code's legacy custom-command surface; Anthropic may eventually require a compatibility update

## How it works

Agent Kickstart is a small stateful harness, not a personality quiz or a single sequential prompt. A project command loads its runtime contract; a local state engine records onboarding checkpoints, safe exit, portrait ownership, and evidence-based changes in guidance. Synthetic fixtures verify that different people receive materially different possibilities.

See [DEMO.md](DEMO.md) for a ten-minute friend demo and [DEVELOPMENT.md](DEVELOPMENT.md) for architecture and test commands.

## About

Kickstart brings Hermes Labs' work to first-time Claude Code users through a guided,
project-local way to begin useful work without having to learn terminal conventions first.

## License

[MIT](LICENSE)
