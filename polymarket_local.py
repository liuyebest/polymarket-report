    # 打印所有环境变量（调试用）
    print("All environment variables:")
    for key, value in os.environ.items():
        if 'TELEGRAM' in key.upper():
            print(f"  {key}: {'***' if 'TOKEN' in key.upper() else value}")
