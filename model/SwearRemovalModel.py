import io
import os
import wave

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types

import librosa
from librosa import display, output
from pydub import AudioSegment


# -------------------------
# GLOBAL SETTINGS
# -------------------------
client = speech.SpeechClient()

list_swear_words = [
    "fuck", "shit", "piss off", "dick", "asshole", "ass",
    "bitch", "bastard", "damn", "cunt", "nigger", "nigga",
    "pussy", "cock"
]


def split_by_percent_pydub(file, folder, layer=1, percent=0.5):
    newAudio = AudioSegment.from_wav(os.path.join(folder, file))

    len_ = len(newAudio)
    slice_index = int(percent * len_)

    audio_slice_1 = newAudio[:slice_index]
    audio_slice_2 = newAudio[slice_index:]

    audio_slice_1.export(os.path.join(folder, "temp_{}_A_pydub.wav".format(layer)), format="wav")
    audio_slice_2.export(os.path.join(folder, "temp_{}_B_pydub.wav".format(layer)), format="wav")


def transcript_contains_swear(transcript):
    for swear in list_swear_words:
        if swear in transcript:
            return True
    return False


def audio_contains_swear(audio, config_, print_=False):
    response = client.recognize(config_, audio)

    if len(response.results) > 0:
        transcript = response.results[0].alternatives[0].transcript
        confidence = response.results[0].alternatives[0].confidence
        swear_in_audio = transcript_contains_swear(transcript)

        if print_:
            print("Transcript: ", transcript)
            print("Confidence: ", confidence)
            print("Does the audio contain a swear word?", swear_in_audio)

        return swear_in_audio
    return False


def split_and_check(files):
    for file_ in files:
        with io.open(file_, 'rb') as audio_file:
            content = audio_file.read()
            audio = types.RecognitionAudio(content=content)

            config = types.RecognitionConfig(
                encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
                language_code='en-US'
            )

            if audio_contains_swear(audio, config):
                return file_
    return None


class SplitCoef:
    def __init__(self, granularity=2):
        self.coefs = self._coefs__(granularity)

    def get_coef(self):
        if len(self.coefs) > 0:
            return self.coefs.pop()
        else:
            return None

    def _sub_coefs__(self, j):  # where j is the granularity
        num_coefs = int((2 ** j) / 2)
        return [(2 * i + 1) / (2 ** j) for i in range(num_coefs)]

    def _coefs__(self, j):
        coefs = []
        for k in range(3, 0, -1):
            coefs += self._sub_coefs__(k)
        return coefs


def apply_block(file, folder, layer, split_coef):
    split_by_percent_pydub(file, folder, layer, split_coef)

    files = [os.path.join(folder, "temp_{}_{}_pydub.wav".format(layer, i)) for i in ["A", "B"]]

    return split_and_check(files)


def calculate_coordinates(m, n, this_split_coef):
    mid_num = int(n - m) * this_split_coef + m
    return [(m, mid_num), (mid_num + 1, n)]


def recursion_block(audio_file_name, start_ind, end_ind, folder, split_granularity=3, recursion_depth=6, layer=0):
    split_coefs = SplitCoef(split_granularity)

    res_audio = audio_file_name

    if recursion_depth > 0:
        while len(split_coefs.coefs) > 0:
            this_coef = split_coefs.get_coef()

            block_results = apply_block(audio_file_name, folder, layer, this_coef)

            if block_results is not None:
                A_coord, B_coord = calculate_coordinates(start_ind, end_ind, this_coef)

                if "A" in block_results:
                    possible_start_ind = A_coord[0]
                    possible_end_ind = A_coord[1]

                elif "B" in block_results:
                    possible_start_ind = B_coord[0]
                    possible_end_ind = B_coord[1]

                block_results = block_results.replace(folder, "")[1:]

                res_audio, start_ind, end_ind = recursion_block(
                    block_results,
                    possible_start_ind,
                    possible_end_ind,
                    folder,
                    split_granularity,
                    recursion_depth - 1,
                    layer + 1
                )

                break

    return res_audio, start_ind, end_ind


def delete_temp_files(folder, recursion_depth):
    for j in range(recursion_depth):
        for i in ["A", "B"]:
            temp_file = os.path.join(folder, "temp_{}_{}_pydub.wav".format(j, i))
            if os.path.isfile(temp_file):
                os.remove(temp_file)


def main(file, folder):

    split_gran = 4
    max_depth = 6

    # can load the wave temporarily to get number of frames
    with wave.open(os.path.join(folder, file)) as temp_file:
        num_frames = temp_file.getnframes()
        frame_rate = temp_file.getframerate()

    out, start, end = recursion_block(file, 0, num_frames, folder, split_gran, max_depth)

    delete_temp_files(folder, max_depth)

    lib_audio, sr = librosa.core.load(os.path.join(folder, file), sr=frame_rate)

    edited_audio = lib_audio.copy()
    edited_audio[int(start):int(end)] = [0] * (int(end) - int(start))

    output.write_wav(os.path.join(folder, "{}_edited.wav".format(file.replace(".wav", ""))), edited_audio, sr=sr)


if __name__ == "__main__":
    folder = "../temp_folder"
    file_name = "trial_audio.wav"
    main(file_name, folder)
