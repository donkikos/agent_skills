#!/usr/bin/env bash
#
# install.sh — symlink selected skills into selected agents' user-level skill dirs.
#
# Skills in this repo live at skills/<name>/SKILL.md. Agents discover skills one
# level deep under their skills dir, so we create:
#     ~/.<agent>/skills/<name> -> <repo>/skills/<name>
#
# Usage:
#   ./install.sh                                  # preview all skills into all agents
#   ./install.sh --yes                            # apply all skills into all agents
#   ./install.sh --yes --agents codex --skills update-changelog
#   ./install.sh --agents claude,codex --skills update-changelog,vastai-cli
#   ./install.sh --list                           # list discovered skills + agent targets
#   ./install.sh -n | --dry-run                   # preview without creating symlinks
#
set -euo pipefail

# --- Resolve repo paths (works from any cwd) ---------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$SCRIPT_DIR/skills"

# --- Agent registry ----------------------------------------------------------
# Add new agents here: name -> target skills directory.
AGENT_NAMES=(claude codex)
agent_dir() {
  case "$1" in
    claude) printf '%s\n' "$HOME/.claude/skills" ;;
    codex)  printf '%s\n' "$HOME/.codex/skills" ;;
    *)      return 1 ;;
  esac
}

# --- Colors (only when stdout is a tty) --------------------------------------
if [[ -t 1 ]]; then
  C_RED=$'\033[31m'; C_GRN=$'\033[32m'; C_YLW=$'\033[33m'; C_DIM=$'\033[2m'; C_RST=$'\033[0m'
else
  C_RED=''; C_GRN=''; C_YLW=''; C_DIM=''; C_RST=''
fi

die() { printf '%serror:%s %s\n' "$C_RED" "$C_RST" "$*" >&2; exit 1; }

# --- Discover skills ---------------------------------------------------------
# A skill is an immediate subdir of skills/ containing a SKILL.md.
discover_skills() {
  local d
  for d in "$SKILLS_DIR"/*/; do
    [[ -f "${d}SKILL.md" ]] || continue
    basename "$d"
  done
}

# --- Argument parsing --------------------------------------------------------
SEL_AGENTS=""
SEL_SKILLS=""
WANT_ALL=0
DO_LIST=0
APPLY=0

usage() {
  sed -n '3,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agents) SEL_AGENTS="${2:-}"; shift 2 ;;
    --agents=*) SEL_AGENTS="${1#*=}"; shift ;;
    --skills) SEL_SKILLS="${2:-}"; shift 2 ;;
    --skills=*) SEL_SKILLS="${1#*=}"; shift ;;
    --all) WANT_ALL=1; shift ;;
    --yes) APPLY=1; shift ;;
    --list) DO_LIST=1; shift ;;
    -n|--dry-run) APPLY=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
done

# --- Gather available items --------------------------------------------------
# Portable read loop (mapfile is unavailable on macOS's stock bash 3.2).
ALL_SKILLS=()
while IFS= read -r skill_line; do
  ALL_SKILLS+=("$skill_line")
done < <(discover_skills)
[[ ${#ALL_SKILLS[@]} -gt 0 ]] || die "no skills found in $SKILLS_DIR"

# --- --list ------------------------------------------------------------------
if [[ $DO_LIST -eq 1 ]]; then
  printf '%sSkills%s (%s)\n' "$C_GRN" "$C_RST" "$SKILLS_DIR"
  for s in "${ALL_SKILLS[@]}"; do printf '  %s\n' "$s"; done
  printf '\n%sAgents%s\n' "$C_GRN" "$C_RST"
  for a in "${AGENT_NAMES[@]}"; do printf '  %-8s -> %s\n' "$a" "$(agent_dir "$a")"; done
  exit 0
fi

# --- Selection helpers -------------------------------------------------------
# Validate a comma-separated list against allowed values; fill named array.
parse_csv_into() {
  local csv="$1" out_name="$2"; shift 2
  local allowed=("$@") tok found result=()
  for tok in ${csv//,/ }; do
    [[ -n "$tok" ]] || continue
    found=0
    for a in "${allowed[@]}"; do [[ "$a" == "$tok" ]] && found=1 && break; done
    [[ $found -eq 1 ]] || die "unknown: '$tok' (valid: ${allowed[*]})"
    result+=("$tok")
  done
  [[ ${#result[@]} -gt 0 ]] || die "nothing selected"
  eval "$out_name=(\"\${result[@]}\")"
}

# --- Resolve final agent + skill selections ----------------------------------
AGENTS=()
SKILLS=()

if [[ $WANT_ALL -eq 1 ]]; then
  AGENTS=("${AGENT_NAMES[@]}")
  SKILLS=("${ALL_SKILLS[@]}")
else
  # Agents
  if [[ -n "$SEL_AGENTS" ]]; then
    parse_csv_into "$SEL_AGENTS" AGENTS "${AGENT_NAMES[@]}"
  else
    AGENTS=("${AGENT_NAMES[@]}")
  fi
  # Skills
  if [[ -n "$SEL_SKILLS" ]]; then
    parse_csv_into "$SEL_SKILLS" SKILLS "${ALL_SKILLS[@]}"
  else
    SKILLS=("${ALL_SKILLS[@]}")
  fi
fi

# --- Install -----------------------------------------------------------------
n_installed=0; n_skipped=0; n_failed=0

link_one() {
  local agent="$1" skill="$2"
  local target_dir src target
  target_dir="$(agent_dir "$agent")"
  src="$SKILLS_DIR/$skill"
  target="$target_dir/$skill"

  if [[ -L "$target" ]]; then
    local cur
    cur="$(readlink "$target")"
    if [[ "$cur" == "$src" ]]; then
      printf '[%s] %-32s %salready installed%s\n' "$agent" "$skill" "$C_DIM" "$C_RST"
      ((n_skipped++)); return 0
    fi
    printf '[%s] %-32s %sskipped%s (symlink -> %s)\n' "$agent" "$skill" "$C_YLW" "$C_RST" "$cur"
    ((n_skipped++)); return 0
  fi
  if [[ -e "$target" ]]; then
    printf '[%s] %-32s %sskipped%s (real path exists)\n' "$agent" "$skill" "$C_YLW" "$C_RST"
    ((n_skipped++)); return 0
  fi

  if [[ $APPLY -eq 0 ]]; then
    printf '[%s] %-32s %swould install%s -> %s\n' "$agent" "$skill" "$C_DIM" "$C_RST" "$target"
    ((n_installed++)); return 0
  fi

  if ! mkdir -p "$target_dir" 2>/dev/null; then
    printf '[%s] %-32s %sfailed%s (cannot create %s)\n' "$agent" "$skill" "$C_RED" "$C_RST" "$target_dir"
    ((n_failed++)); return 1
  fi
  if ln -s "$src" "$target" 2>/dev/null; then
    printf '[%s] %-32s %sinstalled%s\n' "$agent" "$skill" "$C_GRN" "$C_RST"
    ((n_installed++)); return 0
  fi
  printf '[%s] %-32s %sfailed%s (ln error)\n' "$agent" "$skill" "$C_RED" "$C_RST"
  ((n_failed++)); return 1
}

if [[ $APPLY -eq 0 ]]; then
  printf '%s(dry run - no changes made)%s\n' "$C_DIM" "$C_RST"
  printf '%sUse --yes to apply these changes.%s\n' "$C_DIM" "$C_RST"
fi

for agent in "${AGENTS[@]}"; do
  for skill in "${SKILLS[@]}"; do
    link_one "$agent" "$skill" || true
  done
done

if [[ $APPLY -eq 0 ]]; then
  printf '\n%sDone.%s planned=%d skipped=%d failed=%d\n' \
    "$C_GRN" "$C_RST" "$n_installed" "$n_skipped" "$n_failed"
else
  printf '\n%sDone.%s installed=%d skipped=%d failed=%d\n' \
    "$C_GRN" "$C_RST" "$n_installed" "$n_skipped" "$n_failed"
fi

[[ $n_failed -eq 0 ]] || exit 1
