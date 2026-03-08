"""
API 测试示例脚本
用于测试 XMP Server 的各个 API 接口
"""
import requests
import json
from typing import Dict, Optional

# 配置
BASE_URL = "http://localhost:8000"
CUSTOMER_ID = "123-456-7890"  # 替换为你的 Google Ads Customer ID


class XMPClient:
    """XMP Server API 客户端"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()

    def health_check(self) -> Dict:
        """健康检查"""
        response = self.session.get(f"{self.base_url}/health")
        return response.json()

    def list_accounts(self, skip: int = 0, limit: int = 100) -> list:
        """获取账户列表"""
        params = {"skip": skip, "limit": limit}
        response = self.session.get(f"{self.base_url}/api/accounts", params=params)
        response.raise_for_status()
        return response.json()

    def get_account(self, account_id: int) -> Dict:
        """获取单个账户详情"""
        response = self.session.get(f"{self.base_url}/api/accounts/{account_id}")
        response.raise_for_status()
        return response.json()

    def sync_campaigns(self, account_id: int, customer_id: str) -> Dict:
        """同步推广活动"""
        payload = {
            "account_id": account_id,
            "task_type": "CAMPAIGNS",
            "customer_id": customer_id
        }
        response = self.session.post(
            f"{self.base_url}/api/sync/campaigns",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def sync_ad_groups(self, account_id: int, customer_id: str) -> Dict:
        """同步广告组"""
        payload = {
            "account_id": account_id,
            "task_type": "AD_GROUPS",
            "customer_id": customer_id
        }
        response = self.session.post(
            f"{self.base_url}/api/sync/ad-groups",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def get_sync_task(self, task_id: int) -> Dict:
        """查询同步任务状态"""
        response = self.session.get(f"{self.base_url}/api/sync/tasks/{task_id}")
        response.raise_for_status()
        return response.json()

    def list_campaigns(self, account_id: int, skip: int = 0, limit: int = 100) -> list:
        """获取推广活动列表"""
        params = {"account_id": account_id, "skip": skip, "limit": limit}
        response = self.session.get(f"{self.base_url}/api/campaigns", params=params)
        response.raise_for_status()
        return response.json()

    def list_ad_groups(
        self,
        account_id: int,
        campaign_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> list:
        """获取广告组列表"""
        params = {"account_id": account_id, "skip": skip, "limit": limit}
        if campaign_id:
            params["campaign_id"] = campaign_id
        response = self.session.get(f"{self.base_url}/api/ad-groups", params=params)
        response.raise_for_status()
        return response.json()


def print_json(data: Dict):
    """格式化打印 JSON"""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    """主测试流程"""
    print("=" * 60)
    print("XMP Server API 测试")
    print("=" * 60)

    client = XMPClient()

    # 1. 健康检查
    print("\n1. 健康检查")
    print("-" * 60)
    try:
        health = client.health_check()
        print_json(health)
        if health.get("status") != "healthy":
            print("\n⚠️  警告: 系统健康状态异常!")
            return
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return

    # 2. 获取账户列表
    print("\n2. 获取账户列表")
    print("-" * 60)
    try:
        accounts = client.list_accounts()
        print(f"找到 {len(accounts)} 个账户")
        print_json(accounts)

        if not accounts:
            print("\n⚠️  提示: 还没有授权的账户")
            print(f"请访问 {BASE_URL}/auth/authorize?customer_id={CUSTOMER_ID} 进行授权")
            return

        # 使用第一个账户进行后续测试
        account_id = accounts[0]["id"]
        customer_id = accounts[0]["customer_id"]
        print(f"\n将使用账户 ID: {account_id}, Customer ID: {customer_id}")

    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return

    # 3. 获取账户详情
    print("\n3. 获取账户详情")
    print("-" * 60)
    try:
        account = client.get_account(account_id)
        print_json(account)

        if not account.get("has_valid_token"):
            print("\n⚠️  警告: 账户 Token 无效或已过期,需要重新授权")
            return

    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return

    # 4. 同步推广活动
    print("\n4. 同步推广活动")
    print("-" * 60)
    try:
        task = client.sync_campaigns(account_id, customer_id)
        print(f"同步任务已创建, Task ID: {task['id']}")
        print_json(task)

        # 等待任务完成
        import time
        print("\n等待同步完成...")
        for i in range(10):  # 最多等待10秒
            time.sleep(1)
            task_status = client.get_sync_task(task['id'])
            status = task_status['status']
            print(f"任务状态: {status}")

            if status in ['COMPLETED', 'FAILED']:
                print_json(task_status)
                break
        else:
            print("任务仍在运行中...")

    except Exception as e:
        print(f"❌ 错误: {str(e)}")

    # 5. 查询推广活动
    print("\n5. 查询推广活动列表")
    print("-" * 60)
    try:
        campaigns = client.list_campaigns(account_id)
        print(f"找到 {len(campaigns)} 个推广活动")
        if campaigns:
            print("\n前3个推广活动:")
            print_json(campaigns[:3])
    except Exception as e:
        print(f"❌ 错误: {str(e)}")

    # 6. 同步广告组
    print("\n6. 同步广告组")
    print("-" * 60)
    try:
        task = client.sync_ad_groups(account_id, customer_id)
        print(f"同步任务已创建, Task ID: {task['id']}")
        print_json(task)
    except Exception as e:
        print(f"❌ 错误: {str(e)}")

    # 7. 查询广告组
    print("\n7. 查询广告组列表")
    print("-" * 60)
    try:
        ad_groups = client.list_ad_groups(account_id)
        print(f"找到 {len(ad_groups)} 个广告组")
        if ad_groups:
            print("\n前3个广告组:")
            print_json(ad_groups[:3])
    except Exception as e:
        print(f"❌ 错误: {str(e)}")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
