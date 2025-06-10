import urequests
import uhashlib
import utime
import gc

class Senko:
    raw = "https://raw.githubusercontent.com"
    github = "https://github.com"

    def __init__(self, user, repo, url=None, branch="master", working_dir="app", files=["boot.py", "main.py"], headers={}):
        """Senko OTA agent class.

        Args:
            user (str): GitHub user.
            repo (str): GitHub repo to fetch.
            branch (str): GitHub repo branch. (master)
            working_dir (str): Directory inside GitHub repo where the micropython app is.
            url (str): URL to root directory.
            files (list): Files included in OTA update.
            headers (list, optional): Headers for urequests.
        """
        self.base_url = "{}/{}/{}".format(self.raw, user, repo) if user else url.replace(self.github, self.raw)
        self.url = url if url is not None else "{}/{}/{}".format(self.base_url, branch, working_dir)
        self.headers = headers
        self.files = files

    def _check_hash(self, x, y):
        x_hash = uhashlib.sha1(x.encode())
        y_hash = uhashlib.sha1(y.encode())

        x = x_hash.digest()
        y = y_hash.digest()

        if str(x) == str(y):
            return True
        else:
            return False

    def _get_file(self, url):
        try:
            payload = urequests.get(url, headers=self.headers)
            code = payload.status_code

            if code == 200:
                return payload.text
            else:
                print("Got HTTP {} for {}".format(code, url))
                return None
        except Exception as e:
            print("Failed to get file from {}: {}".format(url, e))
            return None

    # ------------------- MODIFIED _check_all METHOD START -------------------

    def _check_all(self):
        """
        Check all files for changes, with retry and memory management.
        """
        changes = []

        for file in self.files:
            latest_version = None
            local_version = None

            # 新增重試機制：最多嘗試 3 次來獲取遠端檔案
            for attempt in range(3):
                content = self._get_file(self.url + "/" + file)
                if content is not None:
                    latest_version = content
                    break  # 成功下載，跳出重試迴圈
                else:
                    print("Failed to check {}, attempt {}/3. Retrying in 1s...".format(file, attempt + 1))
                    utime.sleep(1)

            # 如果 3 次後仍然失敗，則跳過此檔案的檢查
            if latest_version is None:
                print("Could not get remote version of {} after 3 attempts. Skipping check.".format(file))
                gc.collect()
                continue

            # 獲取本地檔案內容
            try:
                with open(file, "r") as local_file:
                    local_version = local_file.read()
            except:
                # 本地端檔案不存在，視為需要更新
                local_version = ""

            # 比對雜湊值
            if not self._check_hash(latest_version, local_version):
                changes.append(file)
            
            # 記憶體回收
            latest_version = None
            local_version = None
            gc.collect()

        return changes

    # -------------------- MODIFIED _check_all METHOD END --------------------

    def fetch(self):
        """Check if newer version is available.

        Returns:
            True - if is, False - if not.
        """
        if not self._check_all():
            return False
        else:
            return True

    def update(self):
        """
        Replace all changed files with newer one, with retry and memory management.
        Returns:
            True - if at least one file was updated, False - if not.
        """
        changes = self._check_all()
        files_updated = [] 

        for file in changes:
            latest_version = None
            
            for attempt in range(3):
                content = self._get_file(self.url + "/" + file)
                if content is not None:
                    latest_version = content
                    break
                else:
                    print("Failed to download {}, attempt {}/3. Retrying in 1s...".format(file, attempt + 1))
                    utime.sleep(1)

            if latest_version is not None:
                try:
                    with open(file, "w") as local_file:
                        local_file.write(latest_version)
                    files_updated.append(file)
                    print("Successfully updated {}.".format(file))
                except Exception as e:
                    print("Failed to write to file {}: {}".format(file, e))
            else:
                print("Could not update {} after 3 attempts. Skipping.".format(file))

            # 記憶體回收
            latest_version = None
            gc.collect()
            print("Memory cleaned up after processing {}.".format(file))

        if files_updated:
            print("Update complete. Updated files: {}".format(files_updated))
            return True
        else:
            if changes:
                 print("Update failed. No files were updated.")
            return False
