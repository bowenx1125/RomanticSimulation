import pandas as pd
from datetime import timedelta
import os


# ==============================
# 1. 读取数据
# ==============================
def load_data(file_path):
    # 表头在第4行（你截图确认的）
    df = pd.read_excel(file_path, header=3)

    # 删除全空行
    df = df.dropna(how='all')

    return df


# ==============================
# 2. 过滤 & 清洗消息
# ==============================
def filter_messages(df):
    """
    保留：
    - 文本消息
    - 引用消息
    - 语音消息（清洗）
    - 其他消息
    """

    filtered_rows = []

    for _, row in df.iterrows():
        msg_type = str(row.get("消息类型", "")).strip()
        content = str(row.get("内容", "")).strip()

        # 跳过空内容
        if not content or content == "nan":
            continue

        # -------------------------
        # 文本 / 引用 / 其他
        # -------------------------
        if msg_type in ["文本消息", "引用消息", "其他消息"]:
            filtered_rows.append(row)
            continue

        # -------------------------
        # 语音消息处理
        # -------------------------
        if msg_type == "语音消息":

            # 去掉前缀
            if "[语音转文字]" in content:
                content = content.replace("[语音转文字]", "").strip()

            # 删除失败语音
            if "转文字失败" in content:
                continue

            # 清洗后为空 → 删除
            if not content:
                continue

            # 写回内容
            row["内容"] = content
            filtered_rows.append(row)

    return pd.DataFrame(filtered_rows)


# ==============================
# 3. 切片（按时间）
# ==============================
def split_segments(df, gap_minutes=30):
    df = df.copy()

    df["时间"] = pd.to_datetime(df["时间"], errors="coerce")
    df = df.sort_values("时间")

    segments = []
    current = []
    prev_time = None

    for _, row in df.iterrows():
        current_time = row["时间"]

        if pd.isna(current_time):
            continue

        if prev_time is None:
            current.append(row)
        else:
            if current_time - prev_time > timedelta(minutes=gap_minutes):
                segments.append(current)
                current = [row]
            else:
                current.append(row)

        prev_time = current_time

    if current:
        segments.append(current)

    return segments


# ==============================
# 4. 生成 Markdown
# ==============================
def build_md(segments):
    md = "## 对话片段\n\n"

    for i, seg in enumerate(segments, 1):
        date_str = seg[0]["时间"].strftime("%Y-%m-%d")
        md += f"### 片段{i}（{date_str}）\n\n"

        for row in seg:
            sender = str(row.get("发送者身份", "")).strip()
            content = str(row.get("内容", "")).strip()

            if content and content != "nan":
                md += f"{sender}: {content}  \n"

        md += "\n---\n\n"

    return md


# ==============================
# 5. 保存文件
# ==============================
def save_md(md_text, input_path):
    output_path = os.path.splitext(input_path)[0] + ".md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_text)

    return output_path


# ==============================
# 6. 主函数
# ==============================
def main():
    input_file = "你的文件.xlsx"   # ← 改这里

    df = load_data(input_file)
    df = filter_messages(df)

    segments = split_segments(df, gap_minutes=30)

    md_text = build_md(segments)
    output_file = save_md(md_text, input_file)

    print(f"✅ 已生成: {output_file}")


if __name__ == "__main__":
    main()