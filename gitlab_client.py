import os
import shutil
import subprocess

import gitlab


class GitlabChanges:

    def __init__(self, gitlab_url, gitlab_token, merge_request_iid, project_id):
        self.gitlab_url = gitlab_url
        self.project_id = project_id
        self.gitlab_token = gitlab_token
        self.merge_request_iid = merge_request_iid

        self.gitlab_api = gitlab.Gitlab(self.gitlab_url, private_token=self.gitlab_token)
        self.source_project_id = self.gitlab_api.projects.get(project_id).mergerequests.get(
            merge_request_iid).source_project_id

        self.merge_request = None
        self.source_branch = None
        self.target_branch = None
        self.changes = []

    def get_merge_request_threads(self):
        merge_request = self.gitlab_api.projects.get(self.project_id).mergerequests.get(self.merge_request_iid)
        threads = merge_request.discussions.list()
        return threads

    def get_merge_request_changes(self):
        self.merge_request = self.gitlab_api.projects.get(self.project_id).mergerequests.get(self.merge_request_iid)
        self.source_branch = self.merge_request.source_branch
        self.target_branch = self.merge_request.target_branch
        self.changes = self.merge_request.changes()['changes']

    def create_merge_request_thread(self, body):
        merge_request = self.gitlab_api.projects.get(self.project_id).mergerequests.get(self.merge_request_iid)
        discussion = merge_request.discussions.create({'body': body})
        return discussion

    def resolve_merge_request_thread(self, thread_id):
        merge_request = self.gitlab_api.projects.get(self.project_id).mergerequests.get(self.merge_request_iid)
        discussions = merge_request.discussions
        discussion = discussions.get(thread_id)
        discussion.resolved = True
        discussion.save()

    @staticmethod
    def clone_repo(repo_url, branch, path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        os.makedirs(path)
        command = ["git", "clone", "-b", branch, repo_url, path]
        subprocess.run(command)

    @staticmethod
    def remove_empty_dirs(path):
        for root, dirs, files in os.walk(path, topdown=False):
            for dirr in dirs:
                dir_path = os.path.join(root, dirr)
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)

        for root, dirs, files in os.walk(path, topdown=False):
            if not dirs and not files:
                os.rmdir(root)

    @staticmethod
    def remove_files_not_in_changes(path, changes, field):
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, path)
                found = False
                for change in changes:
                    if relative_path == change[field]:
                        found = True
                        break
                if not found:
                    os.remove(file_path)

    def run(self, path):
        repo_target = self.get_project_ssh_url(self.project_id)
        repo_source = self.get_project_ssh_url(self.source_project_id)

        path_source = path + "/repo_source"
        path_target = path + "/repo_target"

        self.get_merge_request_changes()
        self.clone_repo(repo_target, self.target_branch, path_target)
        self.clone_repo(repo_source, self.source_branch, path_source)
        self.remove_files_not_in_changes(path_source, self.changes, 'new_path')
        self.remove_files_not_in_changes(path_target, self.changes, 'old_path')
        self.remove_empty_dirs(path_source)
        self.remove_empty_dirs(path_target)

    def get_project_ssh_url(self, project_id):
        return self.gitlab_api.projects.get(project_id).ssh_url_to_repo

    def add_comments(self, comments):
        threads = self.get_merge_request_threads()

        for thread in threads:
            message = thread.attributes['notes'][0]['body']

            if not message.startswith('SONAR_QUBE_ISSUES'):
                continue

            thread_hash = message.split('<br>')[1]
            thread_hash = thread_hash[thread_hash.index(" ") + 1:]

            found = False
            for comment in comments:
                if comment['hash'] == thread_hash:
                    comment['found'] = True
                    found = True
                    break

            if not found:
                self.resolve_merge_request_thread(thread.id)

        for comment in comments:
            if not comment['found']:
                self.create_merge_request_thread(comment['message'])
