from git import Repo, GitCommandError
import os
from github import Auth, GithubIntegration
import traceback


def tag_exists(repo, tag_name):
    """Check if a tag already exists in the repository."""
    return tag_name in [tag.name for tag in repo.tags]


repos = {
    "data-8": [
            "materials-fds-private",
            "materials-fds",
            "materials-fds-colab",
            "materials-fds-binder",
            "materials-fds-jupyterlite",
            "materials-fds-no-footprint",
            "materials-fds-colab-no-footprint",
            "materials-fds-binder-no-footprint",
            "materials-fds-jupyterlite-no-footprint"
    ],
    "ds-modules": [
            "materials-fds-assets"
    ]
}

PR_COMMIT_MESSAGE = "Otter 6.1.3 Configured"
TAG_NAME = 'otter-6.1.3'
TAG_MESSAGE = 'otter-6.1.3'
ROOT_PATH = os.path.dirname(os.getcwd())
# --- GitHub App auth (per org): no personal PAT and no fork ---
_KEY_DIR = os.path.dirname(os.path.abspath(__file__))
APP_CONFIG = {
    "ds-modules": {
        "app_id": 4288757,
        "private_key_path": os.path.join(_KEY_DIR, "ds-modules-app-private-key.pem"),
    },
    "data-8": {
        "app_id": 4289218,
        "private_key_path": os.path.join(_KEY_DIR, "data-8-app-private-key.pem"),
    },
}


def get_app_installation_token(org):
    """Mint a short-lived (~1h) installation token for `org` via its GitHub App."""
    cfg = APP_CONFIG[org]
    with open(cfg["private_key_path"]) as f:
        private_key = f.read()
    gi = GithubIntegration(auth=Auth.AppAuth(cfg["app_id"], private_key))
    installation = gi.get_org_installation(org)
    return gi.get_access_token(installation.id).token


def handle_repo_app(org, r, commit_msg):
    """Publish `r` to `org` using the GitHub App.

    Commits locally and pushes generated content straight to the org repo's
    `main` branch with an installation token. No personal fork and no PR, since
    an org-owned App cannot push to a user's fork.
    """
    repo_path = f"{ROOT_PATH}/{r}"
    print(f"{r} - start (app) =========")
    try:
        token = get_app_installation_token(org)
        push_url = f"https://x-access-token:{token}@github.com/{org}/{r}.git"

        local_repo = Repo(repo_path)
        if local_repo.bare:
            print(f"Local Repository at {repo_path} is bare.")
            return

        local_repo.git.add(A=True)
        if local_repo.is_dirty():
            local_repo.index.commit(commit_msg)

        # Push generated content straight to the org repo's main branch.
        local_repo.git.push(push_url, "HEAD:main", "--force")

        # Refresh the release tag on the org repo.
        try:
            local_repo.git.push(push_url, f":refs/tags/{TAG_NAME}")
        except GitCommandError:
            pass  # remote tag didn't exist yet
        if tag_exists(local_repo, TAG_NAME):
            local_repo.delete_tag(local_repo.tags[TAG_NAME])
        local_repo.create_tag(TAG_NAME, message=TAG_MESSAGE)
        local_repo.git.push(push_url, f"refs/tags/{TAG_NAME}")
    except GitCommandError as e:
        print(f"Git error handling repo: {e}")
    except Exception as e:
        print(traceback.format_exc())
        print(f"Unexpected error: {e}")
    print(f"{r} - done (app) =========")


def main(repo):
    for org, list_repos in repos.items():
        for r in list_repos:
            if not repo or r == repo:
                handle_repo_app(org, r, PR_COMMIT_MESSAGE)


if __name__ == "__main__":
    main(None)  # Pass None to handle all repositories
    print("Changes pulled, committed, and pushed successfully.")
