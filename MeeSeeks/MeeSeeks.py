# installing modules

from difflib import get_close_matches
from wordcloud import STOPWORDS
import pyttsx3
import speech_recognition as sr
import urllib.request
import urllib.parse
import re
import os
from bs4 import BeautifulSoup
import requests
import time
import pywhatkit
import datetime
import wikipedia
import pyjokes
# import ctypes
# Hide the console.
# ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# Libraries

listener = sr.Recognizer()
engine = pyttsx3.init("sapi5")
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)
engine.setProperty('rate', 200)
engine.getProperty('volume')


class Scraper:
    links = []
    names = []

    def __init__(self):
        self.query_dict = dict()

    def get_url(self, url):
        url = requests.get(url).text
        self.soup = BeautifulSoup(url, 'lxml')

    def print_info(self):
        base_url = "https://allrecipes.com/search/results/?"
        query_url = urllib.parse.urlencode(self.query_dict)
        url = base_url + query_url
        self.get_url(url)
        name = self.query_dict['search']

        # Count the number of search results
        resp = self.soup.find(
            'span', class_="search-results-total-results").text.strip(' ')
        resp = ''.join(re.findall('\d+', resp))

        # Check if the search returns no results
        if resp == '0':
            print(f'No recipes found for {name}')
            return

        # Collect all the search results in a BS4 element tag
        articles = self.soup.find_all('div', class_="card__detailsContainer")

        texts = []
        for article in articles:
            txt = article.find('div', class_='card__detailsContainer-left')
            if txt:
                if len(texts) < 5:
                    texts.append(txt)
                else:
                    break
        self.links = [txt.a['href'] for txt in texts]
        self.names = [txt.h3.text for txt in texts]
        self.get_data()

    def get_data(self):
        self.ingredientsList = []
        self.instructionsList = []
        for i, link in enumerate(self.links):
            self.get_url(link)
            self.names[i].lstrip()
            print('-' * 4 + self.names[i] + '-' * 4)
            ingredient_spans = self.soup.find_all(
                'span', class_='ingredients-item-name')
            instructions_spans = self.soup.find_all('div', class_='paragraph')
            ingredients = [span.text.strip() for span in ingredient_spans]
            instructions = [span.text.strip() for span in instructions_spans]

            print('*' * 50)
            self.ingredientsList.append(ingredients)
            self.instructionsList.append(instructions)


class Chef(Scraper):

    def __init__(self):
        self.pause = False

    def get_response(self, text):
        self.keyword = []
        positivesList = {'yes', 'yeah', 'okay', 'yep', 'yup', 'correct'}
        out = 'no'
        result = ''
        print('listening...')
        en_stopwords = list(STOPWORDS) + \
            ["I", "make", "prepare", "cook", "exclude", "include"]
        while 'no' in out:
            response = self.recognize_speech_from_mic(5)
            if response['transcription']:
                inp = response['transcription']
                if 'none' in inp:
                    return ''
                for word in inp.split():
                    if word not in en_stopwords:
                        self.keyword.append(word)
                result = ' '.join(self.keyword)
                self.talk(
                    f"You said {inp}. Is that correct?")
                resp = self.recognize_speech_from_mic(5)
                resp_new = resp['transcription']
                if resp_new:
                    if set(resp_new.split()).intersection(positivesList):
                        out = 'yes'
                        break
                else:
                    self.talk(f"Please repeat {text}")
                    self.keyword = []
                    out = 'no'
            else:
                self.talk(f"I did not catch that. Please repeat {text}")
        return result

    def _command(self):
        self.keyword = []
        self.talk("What recipe would you like to make today?")
        self.name = self.get_response('the recipe Name')
        print(self.name)
        self.talk('Ingredients Include?')
        self.inIncl = self.get_response('the ingredients included')
        print(self.inIncl)
        self.talk('Ingredients Exclude?')
        self.inExcl = self.get_response('the ingredients excluded')
        print(self.inExcl)

        self.query_dict = {
            "search": str(self.name),     # Query keywords
            # 'Must be included' ingrdients (optional)
            "ingIncl": str(self.inIncl),
            # 'Must not be included' ingredients (optional)
            "ingExcl": str(self.inExcl),
            # Sorting options : 're' for relevance,\
            #  'ra' for rating, 'p' for popular (optional)
            "sort": "re"
        }
        self.print_info()

    def pause_reading(self, text):
        self.talk(f"Would you like me to pause while reading the {text}?")
        response = 'no'
        while response == 'no':
            resp = self.recognize_speech_from_mic(2)
            if resp['transcription']:
                pauseResponse = resp['transcription']
                if 'yes' in pauseResponse or 'okay' in pauseResponse:
                    self.pause = True
                    self.talk(f"I will pause while reading the {text}.")
                    print(self.pause)
                    break
                else:
                    self.talk(
                        f"Okay, you chose to not pause. I can still repeat the {text}.")
                    break
            else:
                self.talk("I did not catch that, please repeat.")

    def call_recipes(self):
        self._command()
        self.talk("I found")
        if self.names == []:
            self.talk(f"no recipes matching the request for {self.name}.")
            return
        self.names = [s.rstrip() for s in self.names]
        for i in range(len(self.names)):
            self.talk(self.names[i])
        if self.names:
            self.talk('Which recipe should I read?')
        output = ''
        response = self.recognize_speech_from_mic(5)
        if response['transcription']:
            output = response['transcription']
            print(output)
        index = self.search(output)

        # Read the ingredients List
        self.pause_reading('ingredients')
        response = 'yes'
        while 'yes' in response:
            self.talk("Here is the list of ingredients")
            if self.pause is True:
                self.talk(
                    "I will pause after every ingredient. Please say next, to continue.")
                for ingredient in self.ingredientsList[index]:
                    self.talk(ingredient)
                    engine.runAndWait()
                    resp = self.recognize_speech_from_mic(10)
                    if 'next' in resp['transcription'] or 'continue' in resp['transcription']:
                        pass
            else:
                self.read_ingredients(index)
            self.talk("Would you like me to repeat?")
            resp = self.recognize_speech_from_mic(1)
            response = resp['transcription']
            if 'no' in response:
                self.talk('okay.')
                break
            else:
                self.talk("Please Repeat")

        # Read instructions here
        instructions = '.'.join(self.instructionsList[index])
        self.instructionsList = instructions.rstrip().split('.')
        self.pause = False
        self.pause_reading('instructions')
        response = 'yes'
        while 'yes' in response:
            self.talk("Here are the instructions. ")
            if self.pause is True:
                self.talk(
                    "I will pause after every instruction. Please say next, to continue.")
                for instruction in self.instructionsList:
                    self.talk(instruction)
                    engine.runAndWait()
                    resp = self.recognize_speech_from_mic(10)
                    if 'next' in resp['transcription'] or 'continue' in resp['transcription']:
                        pass
                    else:
                        self.talk("I missed it, moving on...")

            else:
                self.read_instructions()
            self.talk("Would you like me to repeat?")
            resp = self.recognize_speech_from_mic(1)
            response = resp['transcription']
            if 'no' in response:
                self.talk('okay.')
                break
            else:
                self.talk("Please Repeat")
        #
        # Save file
        self.talk("Would you like to save the recipe?")
        response = 'no'
        while 'no' in response:
            resp = self.recognize_speech_from_mic(2)
            if resp['transcription']:
                response = resp['transcription']
                if 'yes' in response:
                    self.save_file(self.names[index], index)
                    self.talk(
                        f'I have saved the recipe in the file {self.names[index]}\
                            .txt')
                    break
            else:
                self.talk("I did not catch that.")

    def save_file(self, recipeName, index):
        recipeNameList = recipeName.split(' ')
        fileName = [recipe+"_" for recipe in recipeNameList]
        fileName = ''.join(fileName) + '.txt'
        print(fileName)
        with open(fileName, 'w', encoding="utf-8") as f:
            f.write(recipeName+"\n")
            f.write("\n")
            f.write("Ingredients\n")
            for ingredient in self.ingredientsList[index]:
                f.write(ingredient+"\n")
            f.write("\n")
            f.write("Instructions" + "\n")
            for instruction in self.instructionsList:
                f.write(instruction + "\n")

    def read_ingredients(self, index):
        for i in range(len(self.ingredientsList[index])):
            print(f"{self.ingredientsList[index][i]}")
            self.talk(f"{self.ingredientsList[index][i]}")

    def read_instructions(self):
        for i in range(len(self.instructionsList)):
            print(f"{self.instructionsList[i]}")
            self.talk(f"{self.instructionsList[i]}")

    def search(self, query):
        # use function to get names that closely match
        match = []
        self.names = [name.lstrip().lower() for name in self.names]
        while match == []:
            match = get_close_matches(query, self.names)
            if match != []:
                break
            self.talk("I did not catch that, Could you repeat again?")
            with sr.Microphone() as source:
                listener.adjust_for_ambient_noise(source, duration=0.5)
                voice = listener.listen(source)
                query = listener.recognize_google(voice, language="en-US")
        for index, name in enumerate(self.names):
            if name == match[0]:
                return index


class MeeSeeks(Chef):

    def __init__(self):
        self.userName = ''
        self.name = ''
        self.inExcl = ''
        self.inIncl = ''
        self.mic = sr.Microphone()
        self.recog = sr.Recognizer()
        self.pause = False

    def talk(self, text):
        engine.say(text)
        engine.runAndWait()

    def recognize_speech_from_mic(self, phrase_time=1):
        """Transcribe speech from recorded from `microphone`.

        Returns a dictionary with three keys:
        "success": a boolean indicating whether or not the API request was
                successful
        "error":   `None` if no error occured, otherwise a string containing
                an error message if the API could not be reached or
                speech was unrecognizable
        "transcription": `None` if speech could not be transcribed,
                otherwise a string containing the transcribed text
        """
        # check that recognizer and microphone arguments are appropriate type
        if not isinstance(self.recog, sr.Recognizer):
            raise TypeError("`recognizer` must be `Recognizer` instance")

        if not isinstance(self.mic, sr.Microphone):
            raise TypeError("`microphone` must be `Microphone` instance")

        # adjust the recognizer sensitivity to ambient noise and record audio
        # from the microphone
        with self.mic as source:
            # analyze the audio source for 1 second
            self.recog.adjust_for_ambient_noise(source, duration=1.5)
            audio = self.recog.listen(
                source, phrase_time_limit=phrase_time)

        # set up the response object
        response = {
            "success": True,
            "error": None,
            "transcription": None
        }

        # try recognizing the speech in the recording
        # if a RequestError or UnknownValueError exception is caught,
        #   update the response object accordingly
        try:
            response["transcription"] = self.recog.recognize_google(
                audio, language="en-UK")
        except sr.RequestError:
            # API was unreachable or unresponsive
            response["success"] = False
            response["error"] = "API unavailable/unresponsive"
        except sr.UnknownValueError:
            # speech was unintelligible
            response["error"] = "Unable to recognize speech"

        return response

    def intro(self):
        self.talk('What would you like to do today?')
        command = ''
        response = self.recognize_speech_from_mic(5)
        commandList = {'bye', 'quit', 'exit', 'see ya', 'ciao', 'tata'}
        if response['transcription']:
            command = response['transcription']
            print(command)
        if 'play' in command:
            song = command.replace('play', '')
            self.talk('playing ' + song)
            pywhatkit.playonyt(song)
        elif 'time' in command:
            time_now = datetime.datetime.now().strftime('%I:%M %p')
            self.talk('Current time is ' + time_now)
        elif 'who is' in command or 'what is' in command or 'search' in command:
            person = command.replace('who the heck is', '')
            info = wikipedia.summary(person, 1)
            print(info)
            self.talk(info)
        elif 'date' in command:
            self.talk('sorry, I have a headache')
        elif 'are you single' in command:
            self.talk('I am in a relationship with wifi')
        elif 'joke' in command:
            self.talk(pyjokes.get_joke())
        elif 'recipe' in command or 'cook' in command or 'make' in command:
            self.call_recipes()
        elif set(command.split(' ')).intersection(commandList):
            self.talk(f'Good bye {self.userName}')
            return False
        else:
            self.talk('Please say the command again.')
        return True

    def wishMe(self):
        hour = int(datetime.datetime.now().hour)
        if hour >= 0 and hour < 12:
            self.talk("Good Morning!")

        elif hour >= 12 and hour < 18:
            self.talk("Good Afternoon!")

        else:
            self.talk("Good Evening!")

        self.talk('I Am Mr. Meeseeks. LOOK AT ME!\
                I am a member of a servant race that exists solely\
                to fulfill whatever task is asked of me. ')
        self.user_name()
        time.sleep(2)

    def user_name(self):
        ''' Sets a username to the user.'''
        self.talk("What should i call you?")
        while self.userName == '':
            response = self.recognize_speech_from_mic(5)
            if response['transcription']:
                # self.talk(f"You said {response['transcription']}")
                self.userName = response['transcription']
            else:
                self.talk("Please repeat.")
        self.talk(f"Welcome {self.userName}")


def main():
    value = True
    chef = MeeSeeks()
    chef.wishMe()
    chef.talk("Here's a list of things I can do. Play a song,\
         search for who a person is, tell the date, tell a joke,\
              or help find a recipe. Say Quit or Exit to quit the app.")

    while value is True:
        value = chef.intro()


if __name__ == '__main__':
    def clear(): return os.system('cls')

    #
    clear()
    main()
