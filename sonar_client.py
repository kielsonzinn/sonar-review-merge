import os
from time import sleep

import requests


class SonarClient:

    def __init__(self, sonar_url, sonar_token):
        self.sonar_url = sonar_url
        self.sonar_token = sonar_token

    def delete_project(self, project_key):
        endpoint = f"{self.sonar_url}/api/projects/delete"
        params = {"project": project_key}
        requests.post(endpoint, params=params, headers=self._get_headers())

    def create_project(self, project_key, project_name):
        endpoint = f"{self.sonar_url}/api/projects/create"
        data = {"project": project_key, "name": project_name}
        response = requests.post(endpoint, params=data, headers=self._get_headers())
        response.raise_for_status()

    def run_scanner(self, project_key, scanner_home, scanner_options, source_path):
        command = f"cd {source_path} && {scanner_home}/bin/sonar-scanner -Dsonar.token={self.sonar_token} -Dsonar" \
                  f".projectKey={project_key} {scanner_options}"
        os.system(command)

    def is_queue_empty(self):
        endpoint = f"{self.sonar_url}/api/analysis_reports/is_queue_empty"
        response = requests.get(endpoint, headers=self._get_headers())
        return response.status_code == 200 and response.json()

    def list_issues(self, project_key):
        endpoint = f"{self.sonar_url}/api/issues/search"
        params = {"componentKeys": project_key, "statuses": "OPEN"}
        response = requests.get(endpoint, params=params, headers=self._get_headers())
        response.raise_for_status()
        return response.json()["issues"]

    def _get_headers(self):
        return {"Authorization": f"Bearer {self.sonar_token}"}

    def get_comments(self, scanner_home, source_path, project_id, merge_request_id):
        __PROJECT_KEY = f"code-review-{project_id}-{merge_request_id}"
        __SCANNER_OPTIONS = "-Dsonar.sources=."

        self.delete_project(__PROJECT_KEY)
        self.create_project(__PROJECT_KEY, __PROJECT_KEY)
        self.run_scanner(__PROJECT_KEY, scanner_home, __SCANNER_OPTIONS, source_path + "/repo_target")

        while not self.is_queue_empty():
            sleep(1)

        issues_target = self.list_issues(__PROJECT_KEY)

        self.run_scanner(__PROJECT_KEY, scanner_home, __SCANNER_OPTIONS, source_path + "/repo_source")

        while not self.is_queue_empty():
            sleep(1)

        issues_source = self.list_issues(__PROJECT_KEY)

        comments = []

        for issue_source in issues_source:
            found = False

            for issue_target in issues_target:
                if issue_source['hash'] == issue_target['hash']:
                    found = True
                    break

            if not found:
                issue_message = issue_source['message']
                issue_hash = issue_source['hash']
                issue_path = issue_source['component']
                issue_path = issue_path[issue_path.index(":") + 1:]
                issue_start_line = issue_source['textRange']['startLine']
                issue_end_line = issue_source['textRange']['endLine']
                details = [
                    "SONAR_QUBE_ISSUES<br>"
                    f"Hash: {issue_hash}",
                    f"Message: {issue_message}",
                    f"Arquivo: {issue_path}",
                    f"Linha inicial: {issue_start_line}",
                    f"Linha final: {issue_end_line}",
                ]
                comments.append({
                    'found': False,
                    'hash': issue_hash,
                    'message': "<br>".join(details)
                })

        self.delete_project(__PROJECT_KEY)

        return comments
