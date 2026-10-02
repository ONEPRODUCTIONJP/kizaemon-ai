import os
import json
import urllib.request
from urllib.error import URLError
from datetime import datetime

def load_env():
    env_vars = dict(os.environ)
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, val = line.split('=', 1)
                    env_vars[key] = val
    except FileNotFoundError:
        pass
    return env_vars

ENV = load_env()

def fetch_nippo_data():
    """Fetch the raw nippo (daily report) data from Supabase Project 2"""
    url = f"{ENV.get('SUPABASE_URL_2')}/rest/v1/kv_store?select=value&key=eq.kizaemon_nippo_history"
    headers = {
        'apikey': ENV.get('SUPABASE_KEY_2', ''),
        'Authorization': f"Bearer {ENV.get('SUPABASE_KEY_2', '')}"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if not data:
                return []
            return data[0]['value']
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def fetch_inventory_data():
    """Fetch inventory and soldout reports from Supabase Project 1"""
    # Note: Implementing just the dummy fetch for now to represent project 1 connection
    return []

# ---------------------------------------------------------
# MCP Tool Functions (Core Logic)
# ---------------------------------------------------------

def get_raw_sales_data(days: int = 7) -> str:
    """
    Get raw sales data for the last N days.
    Allows the AI to see the exact numbers and daily trends.
    """
    data = fetch_nippo_data()
    recent = data[-days:]
    
    result = []
    for d in recent:
        sales = d.get('sales', {})
        total = sales.get('qr', 0) + sales.get('cash', 0) + sales.get('credit', 0)
        perform = d.get('perform', {})
        
        result.append({
            "date": d.get('date'),
            "weather": d.get('weather'),
            "total_sales": total,
            "customers": perform.get('people', 0),
            "soldout_items": [item.get('name') for item in d.get('soldout', [])]
        })
    return json.dumps(result, ensure_ascii=False, indent=2)


def get_sales_statistics(group_by: str = "day_of_week") -> str:
    """
    Get aggregated sales statistics.
    group_by can be 'day_of_week' or 'weather'.
    """
    data = fetch_nippo_data()
    stats = {}
    
    for d in data:
        date_str = d.get('date')
        if not date_str: continue
        sales = d.get('sales', {})
        total = sales.get('qr', 0) + sales.get('cash', 0) + sales.get('credit', 0)
        customers = d.get('perform', {}).get('people', 0)
        
        key = "unknown"
        if group_by == "day_of_week":
            try:
                dt = datetime.strptime(date_str, "%Y/%m/%d")
                # 曜日を日本語で取得
                weekdays = ["月", "火", "水", "木", "金", "土", "日"]
                key = weekdays[dt.weekday()] + "曜日"
            except:
                pass
        elif group_by == "weather":
            key = d.get('weather', 'unknown')

        if key not in stats:
            stats[key] = {"count": 0, "total_sales": 0, "total_customers": 0}
        
        stats[key]["count"] += 1
        stats[key]["total_sales"] += total
        stats[key]["total_customers"] += customers

    result = {}
    for k, v in stats.items():
        if v["count"] > 0:
            result[k] = {
                "average_sales": round(v["total_sales"] / v["count"]),
                "average_customers": round(v["total_customers"] / v["count"]),
                "sample_size_days": v["count"]
            }
            
    return json.dumps(result, ensure_ascii=False, indent=2)


def calculate_baseline_forecast(target_date: str) -> str:
    """
    Calculates a mathematical baseline forecast for a specific date (YYYY/MM/DD).
    Based strictly on historical average for that specific day of the week.
    """
    data = fetch_nippo_data()
    try:
        dt = datetime.strptime(target_date, "%Y/%m/%d")
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        target_weekday = weekdays[dt.weekday()] + "曜日"
    except ValueError:
        return json.dumps({"error": "target_date must be in YYYY/MM/DD format"})
        
    weekday_sales = []
    weekday_customers = []
    
    for d in data:
        try:
            d_dt = datetime.strptime(d.get('date'), "%Y/%m/%d")
            d_weekday = weekdays[d_dt.weekday()] + "曜日"
            
            if d_weekday == target_weekday:
                sales = d.get('sales', {})
                total = sales.get('qr', 0) + sales.get('cash', 0) + sales.get('credit', 0)
                customers = d.get('perform', {}).get('people', 0)
                
                weekday_sales.append(total)
                weekday_customers.append(customers)
        except:
            pass
            
    if not weekday_sales:
        return json.dumps({"error": f"No historical data found for {target_weekday}."})
        
    avg_sales = sum(weekday_sales) / len(weekday_sales)
    avg_customers = sum(weekday_customers) / len(weekday_customers)
    
    return json.dumps({
        "target_date": target_date,
        "target_weekday": target_weekday,
        "baseline_forecast": {
            "expected_sales": round(avg_sales),
            "expected_customers": round(avg_customers)
        },
        "note_to_ai": "これは単なる過去の同一曜日の平均値（ベースライン）です。最終的な予測は、get_raw_sales_data などで直近のトレンドや天気を加味し、あなたの判断で予測レンジ（例：〇〇円〜〇〇円）をユーザーに提案してください。"
    }, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    # 簡単な動作テスト
    print("--- 1. Raw Sales Data (Last 3 days) ---")
    print(get_raw_sales_data(3))
    
    print("\n--- 2. Sales Statistics (By Day of Week) ---")
    print(get_sales_statistics("day_of_week"))
    
    print("\n--- 3. Baseline Forecast for Next Friday (2026/10/02) ---")
    print(calculate_baseline_forecast("2026/10/02"))
