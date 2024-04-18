import streamlit as st
import pandas as pd
import asyncio
from TikTokApi import TikTokApi
import datetime
import plotly.express as px

def convert_timestamp_to_jst(unix_time):
    date = datetime.datetime.utcfromtimestamp(unix_time) + datetime.timedelta(hours=9)
    return date.strftime('%Y-%m-%d %H:%M:%S')

def flatten(data, col_prefix=''):
    flat_dict = {}
    for key, value in data.items():
        if isinstance(value, dict):
            flat_dict.update(flatten(value, col_prefix=col_prefix + key + '_'))
        else:
            flat_dict[col_prefix + key] = value
    return flat_dict

async def sound_videos_to_csv(count, sleep_after, sound_id):
    data_list = []
    async with TikTokApi() as api:
        await api.create_sessions(num_sessions=1, sleep_after=sleep_after)
        async for sound in api.sound(id=sound_id).videos(count=count):
            sound_dict = sound.as_dict
            sound_dict['posted_time_jst'] = convert_timestamp_to_jst(sound_dict.get('createTime', 0))
            flat_sound_dict = flatten(sound_dict)
            data_list.append(flat_sound_dict)
    df = pd.DataFrame(data_list)
    df['posted_time_jst'] = pd.to_datetime(df['posted_time_jst'])
    df = df.sort_values('posted_time_jst')
    return df

st.title("TikTok Sound Video Fetcher and Analyzer")
count = st.number_input("データ数", min_value=1, value=5, step=1)
sleep_after = st.number_input("待機時間", min_value=1, value=5, step=1)
sound_id = st.text_input("サウンドID", value="7194996106114271233")


if st.button("データ取得"):
    df = asyncio.run(sound_videos_to_csv(count, sleep_after, sound_id))
    st.session_state['data'] = df  # セッションステートにデータを保存
    st.success("データが取得されました。")

# データがセッション内に存在する場合のみ、インポート機能を表示
# インポート機能
uploaded_file = st.file_uploader("CSVファイルをアップロードしてください。", type=['csv'])
if uploaded_file is not None:
    uploaded_df = pd.read_csv(uploaded_file)
    st.write("アップロードされたデータ", uploaded_df)
    df = uploaded_df

    # インポートされたデータをセッションに保存
    st.session_state['imported_data'] = uploaded_df
    st.success("データが正常にインポートされました。")
    
    # 日付選択とフィルタリング
    start_date = st.date_input("開始日", value=pd.to_datetime('2021-01-01'))
    end_date = st.date_input("終了日", value=pd.to_datetime('today'))
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    # データがセッション内に存在しない場合のみ、APIからデータを取得
    if 'imported_data' not in st.session_state:
        count = st.number_input("データ数", min_value=1, value=5, step=1)
        sleep_after = st.number_input("待機時間", min_value=1, value=5, step=1)
        sound_id = st.text_input("サウンドID", value="7194996106114271233")

        if st.button("データ取得"):
            df = asyncio.run(sound_videos_to_csv(count, sleep_after, sound_id))
            st.session_state['data'] = df  # セッションステートにデータを保存
            st.success("データが取得されました。")
    
    if 'data' in st.session_state:
        df = st.session_state['data']
        
        filtered_df = df[(df['posted_time_jst'] >= start_date) & (df['posted_time_jst'] <= end_date)]
        st.write("フィルタリングされたデータ", filtered_df)
        
        # 列選択
        all_columns = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        default_columns = ['authorStats_followingCount', 'stats_shareCount', 'stats_collectCount', 
                           'stats_commentCount', 'stats_diggCount', 'stats_playCount']
        options = st.multiselect('グラフに表示するデータを選択してください:', all_columns, default=default_columns)
        
        # グラフ表示
        if options:
            fig = px.line(filtered_df, x='posted_time_jst', y=options,
                          title='選択した期間のメトリクスの時間系列トレンド', labels={'value': 'メトリクス値', 'variable': 'メトリクス'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("表示するデータが選択されていません。")
else:
    st.write("データがまだ取得またはインポートされていません。上のボタンを押してデータを取得またはファイルをアップロードしてください。")