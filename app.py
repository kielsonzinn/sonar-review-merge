import argparse

from gitlab_client import GitlabChanges
from sonar_client import SonarClient

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--GIT_LAB_URL", help="Digite a url do Git Lab")
    parser.add_argument("--GIT_LAB_TOKEN", help="Digite o token do Git Lab")
    parser.add_argument("--GIT_LAB_PROJECT_ID", help="Digite o id do projeto do Git Lab")
    parser.add_argument("--GIT_LAB_MERGE_REQUEST_ID", help="Digite o id do merge request do Git Lab")
    parser.add_argument("--GIT_LAB_REPOSITORY_SOURCE", help="Digite a url do repositorio source")
    parser.add_argument("--GIT_LAB_REPOSITORY_TARGET", help="Digite a url do repositorio target")
    parser.add_argument("--SONAR_QUBE_URL", help="Digite a url do Sonar Qube")
    parser.add_argument("--SONAR_QUBE_TOKEN", help="Digite o token do Sonar Qube")
    parser.add_argument("--SONAR_QUBE_SCANNER_HOME", help="Digite o path do sonnar scanner")
    parser.add_argument("--SOURCE_PATH", help="Digite o path dos projetos")

    args = parser.parse_args()

    gitlab_client = GitlabChanges(
        gitlab_url=args.GIT_LAB_URL,
        gitlab_token=args.GIT_LAB_TOKEN,
        project_id=args.GIT_LAB_PROJECT_ID,
        merge_request_iid=args.GIT_LAB_MERGE_REQUEST_ID,
    )

    gitlab_client.run(
        repo_source=args.GIT_LAB_REPOSITORY_SOURCE,
        repo_target=args.GIT_LAB_REPOSITORY_TARGET,
    )

    comments = SonarClient(
        sonar_token=args.SONAR_QUBE_URL,
        sonar_url=args.SONAR_QUBE_TOKEN,
    ).get_comments(
        scanner_home=args.SONAR_QUBE_SCANNER_HOME,
        source_path=args.SOURCE_PATH,
        project_id=args.GIT_LAB_PROJECT_ID,
        merge_request_id=args.GIT_LAB_MERGE_REQUEST_ID,
    )

    gitlab_client.add_comments(comments)
