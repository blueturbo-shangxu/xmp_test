import requests
import json
import re
import os
from urllib.parse import urlparse, parse_qs

class FeishuRecord:
    def __init__(self):
        self.app_tokne = "UtIzbQhekapOzZsNFXzcm4lxnpg"
        self.app_id = "cli_a43092fdb3e65013"
        self.app_secret = "6odNupIr44FlUiquPSzNLuc5W8gZkjcY"
        self.tenant_access_token = None
        self.base_url = "https://open.feishu.cn/open-apis"

    async def _get_tenant_access_token(self):
        """
        获取 tenant_access_token
        """
        if self.tenant_access_token:
            return self.tenant_access_token

        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        payload = {"app_id": self.app_id, "app_secret": self.app_secret}

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 0:
                self.tenant_access_token = data.get("tenant_access_token")
                print(f"Tenant access token obtained successfully. Expires in {data.get('expire_in')}s.")
                return self.tenant_access_token
            else:
                print(f"Failed to get tenant access token: {data.get('msg')}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Request failed to get tenant access token: {e}")
            return None

    def _parse_sheet_url(self, url: str):
        """
        从飞书表格URL中解析出spreadsheet_token和sheet_id
        """
        # 匹配 spreadsheet_token
        match_spreadsheet = re.search(r'/sheets/([a-zA-Z0-9]+)', url)
        spreadsheet_token = match_spreadsheet.group(1) if match_spreadsheet else None

        # 匹配 sheet_id (工作表ID)
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        sheet_id = query_params.get('sheet', [None])[0]

        if not spreadsheet_token or not sheet_id:
            raise ValueError(f"Could not parse spreadsheet_token or sheet_id from URL: {url}")
        
        print(f"Parsed Spreadsheet Token: {spreadsheet_token}, Sheet ID: {sheet_id}")
        return spreadsheet_token, sheet_id

    async def get_sheet_meta(self, spreadsheet_token: str):
        """
        获取表格的元数据，包括工作表名称和ID
        """
        token = await self._get_tenant_access_token()
        if not token:
            return None

        url = f"{self.base_url}/sheets/v2/spreadsheets/{spreadsheet_token}/metainfo"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 0:
                return data.get("data")
            else:
                print(f"Failed to get sheet meta info: {data.get('msg')}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Request failed to get sheet meta info: {e}")
            return None

    async def read_sheet_data(self, spreadsheet_token: str, sheet_id: str):
        """
        读取指定飞书表格工作表的所有数据
        """
        token = await self._get_tenant_access_token()
        if not token:
            return None

        # 为了获取所有数据，我们通常会指定一个足够大的范围，例如 'A1:ZZZ'
        # 或者，可以先获取metainfo来确定实际的行数和列数，然后构建精确的范围
        # 这里为了简化，我们先尝试一个大范围
        range_str = f"{sheet_id}!A1:E3" 
        url = f"{self.base_url}/sheets/v2/spreadsheets/{spreadsheet_token}/values/{range_str}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 0:
                values = data.get("data", {}).get("valueRange", {}).get("values", [])
                print(f"Successfully read {len(values)} rows from sheet '{sheet_id}'.")
                return values
            else:
                print(f"Failed to read sheet data: {data.get('msg')}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Request failed to read sheet data: {e}")
            return None

    def _extract_file_token_from_drive_url(self, url: str) -> str | None:
        """
        从飞书云空间文件URL中提取 file_token
        示例 URL: https://bluefocus.feishu.cn/drive/file/F-TOKEN
        """
        match = re.search(r'/drive/file/([a-zA-Z0-9_-]+)', url)
        if match:
            return match.group(1)
        return None

    async def download_attachment(self, attachment: dict, save_path: str = "."):
        """
        下载表格中的附件
        attachment 格式: {'fileToken': 'xxx', 'mimeType': 'video/mp4', 'size': 735182, 'text': 'sp_01.mp4', 'type': 'attachment'}
        """
        file_token = attachment.get('fileToken')
        filename = attachment.get('text', f'file_{file_token}')

        if not file_token:
            print("No fileToken found in attachment")
            return None

        token = await self._get_tenant_access_token()
        if not token:
            return None

        # 使用媒体下载API下载附件
        url = f"{self.base_url}/drive/v1/medias/{file_token}/download"
        headers = {
            "Authorization": f"Bearer {token}",
        }

        os.makedirs(save_path, exist_ok=True)

        try:
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()

            file_path = os.path.join(save_path, filename)

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Attachment '{filename}' downloaded successfully to {file_path}")
            return file_path
        except requests.exceptions.RequestException as e:
            print(f"Request failed to download attachment {file_token}: {e}")
            return None

    async def download_feishu_file(self, file_token: str, save_path: str = "./downloads"):
        """
        根据 file_token 下载飞书云空间文件
        """
        token = await self._get_tenant_access_token()
        if not token:
            return None

        url = f"{self.base_url}/drive/v1/files/{file_token}/download"
        headers = {
            "Authorization": f"Bearer {token}",
        }

        os.makedirs(save_path, exist_ok=True)

        try:
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()
            
            # 尝试从响应头中获取文件名
            content_disposition = response.headers.get('Content-Disposition')
            filename = f"file_{file_token}"
            if content_disposition:
                fname_match = re.search(r'filename\*?=(?:UTF-8'')?([^;]+)', content_disposition)
                if fname_match:
                    filename = requests.utils.unquote(fname_match.group(1))
            
            file_path = os.path.join(save_path, filename)

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"File '{filename}' downloaded successfully to {file_path}")
            return file_path
        except requests.exceptions.RequestException as e:
            print(f"Request failed to download file {file_token}: {e}")
            return None

# --- 使用示例 ---
async def main():
    feishu_reader = FeishuRecord()
    
    # 您的飞书表格链接
    sheet_url = "https://bluefocus.feishu.cn/sheets/ApiysvEy3h2gEAtnfMjcdZTznGf?sheet=rGboaJ"
    
    try:
        spreadsheet_token, sheet_id = feishu_reader._parse_sheet_url(sheet_url)
    except ValueError as e:
        print(e)
        return

    # 1. 读取表格数据
    sheet_data = await feishu_reader.read_sheet_data(spreadsheet_token, sheet_id)

    if sheet_data:
        print("\n--- Table Data ---")
        for i, row in enumerate(sheet_data):
            print(f"Row {i+1}: {row}")
            
            # 2. 检查每一行的每个单元格，看是否包含文件URL或附件，并尝试下载
            for j, cell_value in enumerate(row):
                # 检查是否是附件格式 (dict with type='attachment')
                if isinstance(cell_value, dict) and cell_value.get('type') == 'attachment':
                    print(f"  Found attachment in Row {i+1}, Col {j+1}: {cell_value.get('text')}")
                    downloaded_file = await feishu_reader.download_attachment(cell_value)
                    if downloaded_file:
                        print(f"    Downloaded attachment to: {downloaded_file}")
                    else:
                        print(f"    Failed to download attachment: {cell_value.get('text')}")
                # 检查是否是附件列表
                elif isinstance(cell_value, list):
                    for item in cell_value:
                        if isinstance(item, dict) and item.get('type') == 'attachment':
                            print(f"  Found attachment in Row {i+1}, Col {j+1}: {item.get('text')}")
                            downloaded_file = await feishu_reader.download_attachment(item)
                            if downloaded_file:
                                print(f"    Downloaded attachment to: {downloaded_file}")
                            else:
                                print(f"    Failed to download attachment: {item.get('text')}")
                # 检查是否是文件URL
                elif isinstance(cell_value, str) and "feishu.cn/drive/file/" in cell_value:
                    print(f"  Found potential file URL in Row {i+1}, Col {j+1}: {cell_value}")
                    file_token = feishu_reader._extract_file_token_from_drive_url(cell_value)
                    if file_token:
                        print(f"    Extracted file_token: {file_token}")
                        # 尝试下载文件
                        downloaded_file = await feishu_reader.download_feishu_file(file_token)
                        if downloaded_file:
                            print(f"    Downloaded file to: {downloaded_file}")
                        else:
                            print(f"    Failed to download file for token: {file_token}")
                    else:
                        print(f"    Could not extract file_token from URL: {cell_value}")

    else:
        print("Failed to retrieve sheet data.")

# Python 3.7+ 运行异步函数
import asyncio
if __name__ == "__main__":
    asyncio.run(main())
