#!/usr/bin/env bash
# ==============================================================================
# Génération automatique du Changelog (depuis les Conventional Commits)
# ==============================================================================
set -euo pipefail

# Trouve le tag précédent (ex: v1.0.0)
PREV_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

CHANGELOG_FILE="CHANGELOG.md"
TMP_CHANGELOG="/tmp/changelog_draft.md"

echo "[*] Génération du Changelog depuis $PREV_TAG..."

echo "## Unreleased" > "$TMP_CHANGELOG"
echo "*(Généré le $(date -I))*" >> "$TMP_CHANGELOG"
echo "" >> "$TMP_CHANGELOG"

if [ -n "$PREV_TAG" ]; then
    COMMITS_RANGE="${PREV_TAG}..HEAD"
else
    COMMITS_RANGE="HEAD"
fi

# Groupement par types de conventional commits
for TYPE in "feat" "fix" "security" "breaking"; do
    echo "### ${TYPE^^}" >> "$TMP_CHANGELOG"
    # Extrait les commits du type spécifique
    git log "$COMMITS_RANGE" --grep="^${TYPE}:" --grep="^${TYPE}(" --format="- %s ([%h](https://github.com/yourorg/argus-int/commit/%H)) par %an" >> "$TMP_CHANGELOG" || true
    echo "" >> "$TMP_CHANGELOG"
done

# Ajoute ce draft au début du changelog existant
if [ -f "$CHANGELOG_FILE" ]; then
    cat "$CHANGELOG_FILE" >> "$TMP_CHANGELOG"
fi

mv "$TMP_CHANGELOG" "$CHANGELOG_FILE"
echo "✅ Changelog mis à jour dans $CHANGELOG_FILE"
