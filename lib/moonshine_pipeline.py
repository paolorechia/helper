from moonshine_voice import MicTranscriber

class MoonshineRealTimePipeline:
    def __init__(self):
        self.mic = mic = (
            MicTranscriber()    
                .language("en")
                .on_line(self.on_line)
        )
        mic.load()

    def on_line(self, line):
        print(line)
    
    def run_loop(self):
        self.mic.start()
        print("Ready")
        print("*" * 50)
        while True:
            continue