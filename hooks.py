# hooks.py
# 此文件用于定义 python-for-android 构建过程的钩子
from pythonforandroid.toolchain import Logger

def pre_build(dist, *args, **kwargs):
    """
    在所有构建开始前调用
    """
    Logger.info("🔨 开始构建 Pack3D 应用...")
    # 您可以在此处添加自定义的预构建逻辑
    # 例如：Logger.info(f"目标架构: {dist.archs}")

def post_build(dist, *args, **kwargs):
    """
    在所有构建完成后调用
    """
    Logger.info("✅ 应用构建完成！")
    # 您可以在此处添加构建后的处理逻辑

# 注意：函数名（如 pre_build, post_build）是 python-for-android 识别的固定名称。
