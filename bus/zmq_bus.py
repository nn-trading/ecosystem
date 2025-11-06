def smoke():
    try:
        import zmq  # type: ignore
        return True
    except Exception:
        return False
