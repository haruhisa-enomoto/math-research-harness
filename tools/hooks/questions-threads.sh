#!/bin/sh
# Print each thread with staged changes that runs a question-driven program,
# RESEARCH-QUESTIONS.md in the index or HEAD selects this contract, including
# staged deletions. Ordinary QUESTIONS.md catalogs do not. Shared by both hooks.
git diff --cached --name-only --diff-filter=ACMRD -- 'threads/*' \
  | cut -d/ -f1-2 | sort -u \
  | while read -r thread; do
      if git cat-file -e ":$thread/RESEARCH-QUESTIONS.md" 2>/dev/null \
        || git cat-file -e "HEAD:$thread/RESEARCH-QUESTIONS.md" 2>/dev/null; then
        echo "$thread"
      fi
    done
