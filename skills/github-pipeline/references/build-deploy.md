# build-deploy.yml — Docker Build + GKE Deploy

**Customization points**:
- The `build` and `deploy` jobs use `ruh-ai/reusable-workflows-and-charts` reusable workflows by default.
- If the user wants custom steps, replace those `uses:` blocks with their own Docker build + kubectl steps (see the SKILL.md for the example replacement pattern).

```yaml
name: Build and Deploy
run-name: Build and Deploy (${{ github.event.workflow_run.head_branch }})

# Workflow 2 — Triggered automatically when CI (Merge) succeeds on dev, qa, or main.
# CI (Merge) only runs on push events, so this workflow never starts on PRs.
# Approval gate pauses qa and prod deployments until a reviewer approves in GitHub Environments.
#
# ── Variables required ────────────────────────────────────────────────────────
# DEV_URL, QA_URL, PROD_URL
#
# ── GitHub Environments required (Settings > Environments) ────────────────────
# qa   — required reviewers, restrict to qa branch
# prod — required reviewers, restrict to main branch

on:
  workflow_run:
    workflows: ["CI (Merge)"]
    types: [completed]
    branches: [dev, qa, main]

concurrency:
  group: deploy-${{ github.event.workflow_run.head_branch }}
  cancel-in-progress: false

env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"

jobs:
  # Resolves the target environment from the branch and validates that CI passed
  # on a push event (not a PR). All downstream jobs need this one.
  resolve-env:
    name: Resolve Environment
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'success'
    outputs:
      env_name: ${{ steps.resolve.outputs.env_name }}
      base_url: ${{ steps.resolve.outputs.base_url }}
    steps:
      - name: Resolve environment from branch
        id: resolve
        env:
          BRANCH: ${{ github.event.workflow_run.head_branch }}
          PROD_URL: ${{ vars.PROD_URL }}
          QA_URL: ${{ vars.QA_URL }}
          DEV_URL: ${{ vars.DEV_URL }}
        run: |
          if [ "$BRANCH" = "main" ]; then
            echo "env_name=prod" >> $GITHUB_OUTPUT
            echo "base_url=$PROD_URL" >> $GITHUB_OUTPUT
          elif [ "$BRANCH" = "qa" ]; then
            echo "env_name=qa" >> $GITHUB_OUTPUT
            echo "base_url=$QA_URL" >> $GITHUB_OUTPUT
          else
            echo "env_name=dev" >> $GITHUB_OUTPUT
            echo "base_url=$DEV_URL" >> $GITHUB_OUTPUT
          fi

  # Human approval gate for qa and prod. Dev deployments skip this automatically.
  # Configure reviewers at Settings > Environments > qa / prod.
  approval-gate:
    name: Approval Gate (${{ needs.resolve-env.outputs.env_name }})
    needs: resolve-env
    if: |
      needs.resolve-env.outputs.env_name == 'qa' ||
      needs.resolve-env.outputs.env_name == 'prod'
    runs-on: ubuntu-latest
    environment: ${{ needs.resolve-env.outputs.env_name }}
    steps:
      - name: Deployment approved
        run: echo "Deployment to ${{ needs.resolve-env.outputs.env_name }} approved."

  build:
    name: Build (${{ needs.resolve-env.outputs.env_name }})
    needs: [resolve-env, approval-gate]
    # always() lets this run even when approval-gate was skipped (dev branch).
    if: |
      always() &&
      needs.resolve-env.result == 'success' &&
      (needs.approval-gate.result == 'success' || needs.approval-gate.result == 'skipped')
    permissions:
      contents: read
      id-token: write
    uses: ruh-ai/reusable-workflows-and-charts/.github/workflows/reusable-build.yaml@workflow/v1.3.1
    secrets: inherit

  deploy:
    name: Deploy (${{ needs.resolve-env.outputs.env_name }})
    needs: [resolve-env, build]
    if: |
      always() &&
      needs.resolve-env.result == 'success' &&
      needs.build.result == 'success'
    permissions:
      contents: read
      id-token: write
    uses: ruh-ai/reusable-workflows-and-charts/.github/workflows/reusable-deploy-gke.yaml@workflow/v1.3.1
    secrets: inherit
```

## Custom Build/Deploy Alternative

If the user is NOT using `ruh-ai/reusable-workflows-and-charts`, replace the `build` and `deploy` jobs with:

```yaml
  build:
    name: Build (${{ needs.resolve-env.outputs.env_name }})
    needs: [resolve-env, approval-gate]
    if: |
      always() &&
      needs.resolve-env.result == 'success' &&
      (needs.approval-gate.result == 'success' || needs.approval-gate.result == 'skipped')
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - name: Build and push Docker image
        env:
          DOCKER_REGISTRY: ${{ secrets.DOCKER_REGISTRY }}
          IMAGE_TAG: ${{ secrets.DOCKER_REGISTRY }}/app:${{ github.sha }}
        run: |
          docker build -t $IMAGE_TAG .
          docker push $IMAGE_TAG
      - name: Save image tag
        run: echo "image_tag=$IMAGE_TAG" >> $GITHUB_OUTPUT
        id: image

  deploy:
    name: Deploy (${{ needs.resolve-env.outputs.env_name }})
    needs: [resolve-env, build]
    if: |
      always() &&
      needs.resolve-env.result == 'success' &&
      needs.build.result == 'success'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Kubernetes
        env:
          IMAGE_TAG: ${{ secrets.DOCKER_REGISTRY }}/app:${{ github.sha }}
        run: kubectl set image deployment/app app=$IMAGE_TAG
```
