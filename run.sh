#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
PARAS=${1:-1000}
nix run .#spacy -- "$PARAS"
echo
nix run .#resharp -- "$PARAS"
