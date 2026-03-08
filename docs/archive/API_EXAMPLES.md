# API 使用示例

本文档提供各种场景下的 API 使用示例。

## 目录

1. [授权流程](#授权流程)
2. [账户管理](#账户管理)
3. [数据同步](#数据同步)
4. [数据查询](#数据查询)
5. [Python 客户端示例](#python-客户端示例)

---

## 授权流程

### 场景1: 通过 Web 界面授权

1. 访问首页: http://localhost:8000
2. 输入 Customer ID: `123-456-7890`
3. 点击"开始授权"按钮
4. 在 Google 页面登录并授权
5. 授权成功后自动返回系统

### 场景2: 通过 API 直接授权

```bash
# 跳转到授权页面
curl "http://localhost:8000/auth/authorize?customer_id=123-456-7890"

# 或者不指定 customer_id,稍后配置
curl "http://localhost:8000/auth/authorize"
```

---

## 账户管理

### 获取所有账户

```bash
curl http://localhost:8000/api/accounts
```

**响应示例:**
```json
[
  {
    "id": 1,
    "customer_id": "123-456-7890",
    "account_name": "My Google Ads Account",
    "currency_code": "USD",
    "timezone": "America/New_York",
    "account_type": "CLIENT",
    "status": "ACTIVE",
    "has_valid_token": true,
    "created_at": "2024-01-01T10:00:00"
  }
]
```

### 获取单个账户详情

```bash
curl http://localhost:8000/api/accounts/1
```

### 分页查询账户

```bash
# 跳过前10条,获取20条
curl "http://localhost:8000/api/accounts?skip=10&limit=20"
```

---

## 数据同步

### 同步推广活动

```bash
curl -X POST http://localhost:8000/api/sync/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "task_type": "CAMPAIGNS",
    "customer_id": "123-456-7890"
  }'
```

**响应示例:**
```json
{
  "id": 1,
  "account_id": 1,
  "task_type": "CAMPAIGNS",
  "status": "COMPLETED",
  "total_records": 25,
  "processed_records": 25,
  "failed_records": 0,
  "started_at": "2024-01-01T10:00:00",
  "completed_at": "2024-01-01T10:00:15",
  "error_message": null
}
```

### 同步广告组

```bash
curl -X POST http://localhost:8000/api/sync/ad-groups \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": 1,
    "task_type": "AD_GROUPS",
    "customer_id": "123-456-7890"
  }'
```

### 查询同步任务状态

```bash
curl http://localhost:8000/api/sync/tasks/1
```

**使用场景:**
- 监控长时间运行的同步任务
- 检查同步是否完成
- 查看错误信息

---

## 数据查询

### 查询推广活动

```bash
# 基本查询
curl "http://localhost:8000/api/campaigns?account_id=1"

# 分页查询
curl "http://localhost:8000/api/campaigns?account_id=1&skip=0&limit=50"
```

**响应示例:**
```json
[
  {
    "id": 1,
    "campaign_id": "12345678",
    "campaign_name": "Summer Sale Campaign",
    "campaign_status": "ENABLED",
    "campaign_type": "SEARCH",
    "advertising_channel_type": "SEARCH",
    "budget_amount": "100.00",
    "bidding_strategy_type": "TARGET_CPA",
    "start_date": "2024-01-01",
    "end_date": null,
    "serving_status": "SERVING",
    "last_synced_at": "2024-01-01T10:00:15"
  }
]
```

### 查询广告组

```bash
# 查询所有广告组
curl "http://localhost:8000/api/ad-groups?account_id=1"

# 查询特定推广活动的广告组
curl "http://localhost:8000/api/ad-groups?account_id=1&campaign_id=1"

# 分页查询
curl "http://localhost:8000/api/ad-groups?account_id=1&skip=0&limit=50"
```

**响应示例:**
```json
[
  {
    "id": 1,
    "campaign_id": 1,
    "ad_group_id": "87654321",
    "ad_group_name": "Brand Keywords",
    "ad_group_status": "ENABLED",
    "ad_group_type": "SEARCH_STANDARD",
    "cpc_bid_micros": 1500000,
    "cpm_bid_micros": null,
    "target_cpa_micros": 5000000,
    "last_synced_at": "2024-01-01T10:01:30"
  }
]
```

---

## Python 客户端示例

### 基本使用

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. 健康检查
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# 2. 获取账户列表
response = requests.get(f"{BASE_URL}/api/accounts")
accounts = response.json()
print(f"账户数量: {len(accounts)}")

# 3. 同步推广活动
account_id = accounts[0]["id"]
customer_id = accounts[0]["customer_id"]

payload = {
    "account_id": account_id,
    "task_type": "CAMPAIGNS",
    "customer_id": customer_id
}
response = requests.post(f"{BASE_URL}/api/sync/campaigns", json=payload)
task = response.json()
print(f"同步任务ID: {task['id']}")

# 4. 查询推广活动
params = {"account_id": account_id}
response = requests.get(f"{BASE_URL}/api/campaigns", params=params)
campaigns = response.json()
print(f"推广活动数量: {len(campaigns)}")
```

### 使用封装的客户端

```python
from test_api import XMPAuthClient

# 创建客户端
client = XMPAuthClient("http://localhost:8000")

# 健康检查
health = client.health_check()
print(health)

# 获取账户
accounts = client.list_accounts()
account_id = accounts[0]["id"]
customer_id = accounts[0]["customer_id"]

# 同步数据
task = client.sync_campaigns(account_id, customer_id)
print(f"Task ID: {task['id']}")

# 查询数据
campaigns = client.list_campaigns(account_id)
print(f"找到 {len(campaigns)} 个推广活动")
```

### 完整的工作流程

```python
import requests
import time

BASE_URL = "http://localhost:8000"

def complete_workflow():
    """完整的数据同步工作流程"""

    # 1. 获取账户
    accounts = requests.get(f"{BASE_URL}/api/accounts").json()
    if not accounts:
        print("没有授权的账户")
        return

    account = accounts[0]
    account_id = account["id"]
    customer_id = account["customer_id"]

    # 2. 同步推广活动
    print("开始同步推广活动...")
    task_data = {
        "account_id": account_id,
        "task_type": "CAMPAIGNS",
        "customer_id": customer_id
    }
    campaign_task = requests.post(
        f"{BASE_URL}/api/sync/campaigns",
        json=task_data
    ).json()

    # 3. 等待同步完成
    while True:
        task_status = requests.get(
            f"{BASE_URL}/api/sync/tasks/{campaign_task['id']}"
        ).json()

        status = task_status["status"]
        print(f"推广活动同步状态: {status}")

        if status in ["COMPLETED", "FAILED"]:
            break

        time.sleep(2)

    if task_status["status"] == "FAILED":
        print(f"同步失败: {task_status['error_message']}")
        return

    print(f"成功同步 {task_status['processed_records']} 个推广活动")

    # 4. 同步广告组
    print("开始同步广告组...")
    task_data["task_type"] = "AD_GROUPS"
    ad_group_task = requests.post(
        f"{BASE_URL}/api/sync/ad-groups",
        json=task_data
    ).json()

    # 5. 等待同步完成
    while True:
        task_status = requests.get(
            f"{BASE_URL}/api/sync/tasks/{ad_group_task['id']}"
        ).json()

        status = task_status["status"]
        print(f"广告组同步状态: {status}")

        if status in ["COMPLETED", "FAILED"]:
            break

        time.sleep(2)

    if task_status["status"] == "FAILED":
        print(f"同步失败: {task_status['error_message']}")
        return

    print(f"成功同步 {task_status['processed_records']} 个广告组")

    # 6. 查询同步的数据
    campaigns = requests.get(
        f"{BASE_URL}/api/campaigns",
        params={"account_id": account_id}
    ).json()

    ad_groups = requests.get(
        f"{BASE_URL}/api/ad-groups",
        params={"account_id": account_id}
    ).json()

    print(f"\n同步结果:")
    print(f"- 推广活动: {len(campaigns)} 个")
    print(f"- 广告组: {len(ad_groups)} 个")

    # 7. 显示示例数据
    if campaigns:
        print(f"\n示例推广活动:")
        campaign = campaigns[0]
        print(f"  名称: {campaign['campaign_name']}")
        print(f"  状态: {campaign['campaign_status']}")
        print(f"  预算: {campaign['budget_amount']}")

    if ad_groups:
        print(f"\n示例广告组:")
        ad_group = ad_groups[0]
        print(f"  名称: {ad_group['ad_group_name']}")
        print(f"  状态: {ad_group['ad_group_status']}")

if __name__ == "__main__":
    complete_workflow()
```

---

## 错误处理示例

### 处理 HTTP 错误

```python
import requests

try:
    response = requests.get("http://localhost:8000/api/accounts/999")
    response.raise_for_status()  # 如果状态码不是2xx,抛出异常
    data = response.json()
except requests.exceptions.HTTPError as e:
    print(f"HTTP错误: {e}")
    print(f"响应内容: {e.response.json()}")
except requests.exceptions.ConnectionError:
    print("无法连接到服务器")
except requests.exceptions.Timeout:
    print("请求超时")
except Exception as e:
    print(f"未知错误: {e}")
```

### 处理同步失败

```python
def sync_with_retry(account_id, customer_id, max_retries=3):
    """带重试的同步"""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "http://localhost:8000/api/sync/campaigns",
                json={
                    "account_id": account_id,
                    "task_type": "CAMPAIGNS",
                    "customer_id": customer_id
                },
                timeout=30
            )
            response.raise_for_status()

            task = response.json()
            # 等待任务完成
            # ... (等待逻辑)

            return task

        except Exception as e:
            print(f"尝试 {attempt + 1}/{max_retries} 失败: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(5)  # 等待5秒后重试
```

---

## 批量操作示例

### 批量同步多个账户

```python
import requests
import concurrent.futures

def sync_account(account):
    """同步单个账户"""
    account_id = account["id"]
    customer_id = account["customer_id"]

    print(f"开始同步账户: {account['account_name']}")

    # 同步推广活动
    requests.post(
        "http://localhost:8000/api/sync/campaigns",
        json={
            "account_id": account_id,
            "task_type": "CAMPAIGNS",
            "customer_id": customer_id
        }
    )

    # 同步广告组
    requests.post(
        "http://localhost:8000/api/sync/ad-groups",
        json={
            "account_id": account_id,
            "task_type": "AD_GROUPS",
            "customer_id": customer_id
        }
    )

    print(f"完成同步账户: {account['account_name']}")

# 获取所有账户
accounts = requests.get("http://localhost:8000/api/accounts").json()

# 使用线程池并行同步
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(sync_account, accounts)

print("所有账户同步完成!")
```

---

## 更多示例

查看项目中的 `test_api.py` 文件获取完整的测试示例。

运行测试脚本:

```bash
python test_api.py
```

该脚本会自动测试所有主要的 API 功能。
