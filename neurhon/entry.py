import neurhon.data_aquisition.livestream as ls
def run():
    stream = sa.LiveStreamAnalyzer(device_name="BA MINI 77",timeframe=0.5)
    stream.start_streaming()
    stream.kill_yourself()
