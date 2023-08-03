import os
import openai
import re
import random
import time
import logging
from flask import current_app
openai.api_key = "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"

class Scene:

    def __init__(self, social_skill, goals, logger):

        self.social_skill = social_skill
        self.goals = goals 

        self.overview = ""
        self.narration = ""
        self.location = ""
        self.background = ""
        self.current_event = ""
        self.characters = {}
        self.character_images = {}
        self.past_messages = []
        self.future_messages = []
        self.someone_left = False
        self.last_round = False
        self.end = False

        self.scores = []

        self.score_totals = {}
        self.logger = logger
        
    def as_dict(self):
        return {
            "social_skill": self.social_skill,
            "goals": self.goals,
            "overview": self.overview,
            "narration": self.narration,
            "location": self.location,
            "background": self.background,
            "current_event": self.current_event,
            "characters": self.characters,
            "character_images": self.character_images,
            "past_messages": self.past_messages,
            "future_messages": self.future_messages,
            "scores": [score_string(score) for score in self.scores],
            "score_totals": self.score_totals,
            "someone_left": self.someone_left,
            "last_round": self.last_round,
            "end": self.end
        }


    # Goal tracker

    def process_conversation(self, messages, aps=False, sot=False):

        def tracker_response(message_prompt, temperature=0):
            openai.api_key = "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"
            completion = openai.ChatCompletion.create(
                model="gpt-4",
                messages=message_prompt
            )
            return completion['choices'][0]['message']['content'].lower()

        # Initialize metrics

        metrics = {}

        # Processing for addressing prior statement

        if aps:

            addressing_prompt = [
                {"role": "system", "content": "You are a helpful AI"},
                {"role": "user",
                "content": f"Based on this conversation context: {messages} does the last Student message directly addresses a prior statement from the Assistant with a comment or question? Only answer with one word: question, comment, both or no"}
            ]


            metrics["addressing_prior_statement"] = {"comment_count": 0, "question_count": 0, "no_comment_count": 0}

            addressing_result = tracker_response(addressing_prompt)

            if addressing_result == 'comment':
                metrics["addressing_prior_statement"]["comment_count"] += 1
            elif addressing_result == 'question':
                metrics["addressing_prior_statement"]["question_count"] += 1
            elif addressing_result == 'both':
                metrics["addressing_prior_statement"]["question_count"] += 1
                metrics["addressing_prior_statement"]["comment_count"] += 1
            elif addressing_result == 'no':
                metrics["addressing_prior_statement"]["no_comment_count"] += 1

        # Processing for staying on topic

        if sot:

            topic_prompt = [
                {"role": "system", "content": "You are a helpful AI"},
                {"role": "user",
                "content": f"Based on this conversation context: {messages} is the last Student message on topic? Answer 'yes' 'no' or 'unclear'."}
            ]

            metrics["staying_on_topic"] = {"on_topic": 0, "off_topic": 0, "unclear": 0}

            topic_result = tracker_response(topic_prompt)

            if topic_result == 'yes':
                metrics["staying_on_topic"]["on_topic"] += 1
            elif topic_result == 'no':
                metrics["staying_on_topic"]["off_topic"] += 1
            elif topic_result == 'unclear':
                metrics["staying_on_topic"]["unclear"] += 1

        return metrics

    # Helpers

    def parse_output(self, output: str, keyword: str) -> str:

        if keyword + ":" not in output:
            return ""

        return output.split(keyword + ":")[-1].split("###")[0].strip()

    def parse_character_output(self, output: str, keyword: str) -> str:

        if keyword + ":" not in output:
            return ""

        return output.split(keyword + ":")[-1].split("\n")[0].strip()

    def parse_characters(self, characters_response):
        characters = {}

        for character in characters_response.split("$")[1:]:
            characters[self.parse_character_output(character.strip(), "Name")] = {
                "Gender": self.parse_character_output(character.strip(), "Gender"),
                "Personality": self.parse_character_output(character.strip(), "Personality")
            }

        return characters

    def parse_character_roles(self, updated_character_roles):
        roles = {}

        for character in updated_character_roles.split("$")[1:]:
            parts = character.split(":")
            name, role = parts[0], ":".join(parts[1:])
            roles[name.strip()] = role.strip()

        return roles

    def assign_character_images(self):

        self.character_images = {}

        image_ids = ["1", "2", "3", "4"]
        random.shuffle(image_ids)

        male_id = 0
        female_id = 0

        for (name, character) in self.characters.items():

            if name == "Student":
                continue

            if character["Gender"] == "Male":
                self.character_images[name] = "c_male_" + image_ids[male_id]
                male_id += 1
                if male_id == 4:
                    male_id = 0
            else:
                self.character_images[name] = "c_female_" + image_ids[female_id]
                female_id += 1
                if female_id == 4:
                    female_id = 0

    def assign_background(self):

        background_map = {
            "classroom": "bg_classroom",
            "cafeteria": "bg_cafeteria",
            "train": "bg_train",
            "bus": "bg_bus",
            "street": "bg_street",
            "coffee": "bg_coffee_shop",
            "shop": "bg_coffee_shop"
        }

        self.background = "bg_classroom"

        for keyword, asset in background_map.items():
            if keyword in self.location.lower():
                self.background = asset
                break

    def parse_conversation(self, conversation):
        self.interactions = []

        for interaction in conversation.strip().split("$")[1:]:
            parts = interaction.split(":")
            name, message = parts[0], ":".join(parts[1:])

            self.interactions.append((name.strip(), message.strip()))

        return self.interactions
    
    def score_string(self, score):
        ss = ""

        if "addressing_prior_statement" in self.goals and self.goals["addressing_prior_statement"]:
            ss = "Addressing Prior Statements:\n"
            ss += f'- Comment Count: {score["data"]["addressing_prior_statement"]["comment_count"]}\n'
            ss += f'- Question Count: {score["data"]["addressing_prior_statement"]["question_count"]}\n'
            ss += f'- No Comment Count: {score["data"]["addressing_prior_statement"]["no_comment_count"]}\n'

        if "staying_on_topic" in self.goals and self.goals["staying_on_topic"]:
            ss += "Staying on Topic:\n"
            ss += f'- On Topic: {score["data"]["staying_on_topic"]["on_topic"]}\n'
            ss += f'- Off Topic: {score["data"]["staying_on_topic"]["off_topic"]}\n'
            ss += f'- Unclear: {score["data"]["staying_on_topic"]["unclear"]}'

        if ss == "":
            ss = "No goals to track"

        return {
            "message": score["message"],
            "data": ss
        }

    def add_score_to_total(self, score):

        if "addressing_prior_statement" in self.goals and self.goals["addressing_prior_statement"]:

            if "addressing_prior_statement" not in self.score_totals:
                self.score_totals["addressing_prior_statement"] = {
                    "comment_count": 0,
                    "question_count": 0,
                    "no_comment_count": 0
                }

            self.score_totals["addressing_prior_statement"]["comment_count"] += score["addressing_prior_statement"]["comment_count"]
            self.score_totals["addressing_prior_statement"]["question_count"] += score["addressing_prior_statement"]["question_count"]
            self.score_totals["addressing_prior_statement"]["no_comment_count"] += score["addressing_prior_statement"]["no_comment_count"]

            # End scene if goal reached

            if self.score_totals["addressing_prior_statement"]["comment_count"] + self.score_totals["addressing_prior_statement"]["question_count"] > 0:
                self.current_event = "One of the people in the conversation needs to leave and the scenario must end thereafter."
                self.last_round = True

 
        if "staying_on_topic" in self.goals and self.goals["staying_on_topic"]:

            if "staying_on_topic" not in self.score_totals:
                self.score_totals["staying_on_topic"] = {
                    "on_topic": 0,
                    "off_topic": 0,
                    "unclear": 0
                }

            self.score_totals["staying_on_topic"]["on_topic"] += score["staying_on_topic"]["on_topic"]
            self.score_totals["staying_on_topic"]["off_topic"] += score["staying_on_topic"]["off_topic"]
            self.score_totals["staying_on_topic"]["unclear"] += score["staying_on_topic"]["unclear"]

            # End scene if goal reached

            if self.score_totals["staying_on_topic"]["on_topic"] > 0:
                self.current_event = "One of the people in the conversation needs to leave and the scenario must end thereafter."
                self.last_round = True
 

    # Scene Setup

    def generate_scene(self):

        # Create input string
        selected_goals = [goal for (goal, is_selected) in self.goals.items() if is_selected]

        goals_string = "No specific goals"
        if len(selected_goals) != 0:
            selected_goals = [
                "Address prior statements" if goal == "addressing_prior_statement" else "Staying on topic"
                for goal in selected_goals
            ]
            goals_string = "\n".join(["- " + goal for goal in selected_goals])
        
        user_input = f"""Here is the social skill that needs to be learned and an optional set of goals or metrics to evaluate it. Come up with a suitable scenario and provide all the required information as described.\nThe social skill that needs to be learned: {self.social_skill}\nA set of goals to evaluate the skill:\n{goals_string}"""

        # Load prompt

        with open("./prompts/scene_setup.p") as f:
            prompt = f.read()
        
        completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
            "role": "system", 
            "content": prompt
            },
            {
            "role": "user", 
            "content": user_input
            }
        ]
        )

        response = completion["choices"][0]["message"].content

        # Parse Outputs

        self.overview = self.parse_output(response, "Overview")
        
        self.location = self.parse_output(response, "Location")
        self.assign_background()

        characters_response = self.parse_output(response, "Characters")
        self.characters = self.parse_characters(characters_response)
        self.assign_character_images()

        self.narration = self.parse_output(response, "Narration")
        self.current_event = self.parse_output(response, "Short-term Event Summary")

        roles_string = self.parse_output(response, "How Each Character Should Act in the Short term")
        character_roles = self.parse_character_roles(roles_string)

        for name, role in character_roles.items():

            if name in self.characters:
                self.characters[name]["Role"] = role


    # Scene Manager

    def update_scene(self):

        # Create input string

        characters_string = ""
        for name, character in self.characters.items():
            characters_string += f"\n$ Name: {name}\nGender: {character['Gender']}\nGeneral Personality: {character['Personality']}"
        
        conversation = ""
        for (name, interaction) in self.past_messages:
            conversation += f"\n$ {name}: {interaction}"

        message = f"""Here are the details about a certain scenario. Watch over the interactions and describe the current or near future interactions that should take place and how each character should act.
        Overview of the Scenario: {self.overview}
        Where the scenario is taking place: {self.location}
        The people involved in the scenario and their attributes:{characters_string}
        Entire Past Conversation:{conversation}"""

        # Load prompt

        with open("./prompts/scene_manager.p") as f:
            prompt = f.read()

        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": message
                }
            ]
        )

        response = completion["choices"][0]["message"].content

        # Parse Outputs

        updated_event = self.parse_output(response, "Short-term Event Summary")

        has_someone_left = self.parse_output(response, "Has Any Character Already Left the Scene")
        self.someone_left = "yes" in has_someone_left

        updated_character_roles = self.parse_output(response, "How Each Character Should Act in the Short term")
        character_roles = self.parse_character_roles(updated_character_roles)

        self.current_event = updated_event

        for name, role in character_roles.items():

            if name in self.characters:
                self.characters[name]["Role"] = role


    # Conversation Generator

    def generate_conversation(self):

        # Create input string

        characters_string = ""
        for name, character in self.characters.items():
            characters_string += f"\n$ Name: {name}\nGender: {character['Gender']}\nGeneral Personality: {character['Personality']}\nHow to Act Now: {character['Role']}"
        
        conversation = ""
        for (name, interaction) in self.past_messages:
            conversation += f"\n$ {name}: {interaction}"

        message = f"""Here are the details about a certain conversation. Generate the next 5 messages that would logically follow.
        Context of the Conversation: {self.overview}
        Where the conversation is taking place: {self.location}
        The people involved in the conversation and their attributes: {characters_string}
        Short-term Event Summary: {self.current_event}
        Entire Past Conversation:\n{conversation}"""

        # Load prompt

        with open("./prompts/conversation_generator.p") as f:
            prompt = f.read()

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": message
                }
            ]
        )

        response = completion["choices"][0]["message"].content

        # Parse Outputs

        self.future_messages = self.parse_conversation(self.parse_output(response, "Next Messages"))

    # Conversation Ender

    def conversation_ender(self):

        # Create input string

        characters_string = ""
        for name, character in self.characters.items():
            characters_string += f"\n$ Name: {name}\nGender: {character['Gender']}\nGeneral Personality: {character['Personality']}"
        
        conversation = ""
        for (name, interaction) in self.past_messages:
            conversation += f"\n$ {name}: {interaction}"

        message = f"""Here are the details about a certain conversation. Generate the a list of messages that would logically follow this conversation and would bring it to an end in a minimum number of messages.
        Context of the Conversation: {self.overview}
        Where the conversation is taking place: {self.location}
        The people involved in the conversation and their attributes: {characters_string}
        Entire Past Conversation:\n{conversation}"""

        # Load prompt

        with open("./prompts/conversation_ender.p") as f:
            prompt = f.read()

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": message
                }
            ]
        )

        response = completion["choices"][0]["message"].content

        print(response)

        # Parse Outputs

        self.future_messages = self.parse_conversation(self.parse_output(response, "Messages Until Conversation End"))
        self.last_round = True


    # UI Manager

    def interact(self, user_spoke: bool, message: str):

        print("Current Event: ", self.current_event)
        print("Has Someone Left: ", self.someone_left)
        print("Last Round?: ", self.last_round)
        print("End?: ", self.end)
        
        # End handling
        
        if self.someone_left or "[END]" in self.current_event:
            return ["END", "THE END"], self.characters["Student"]["Role"]

        if self.end:

            if len(self.future_messages) == 0:
                return ["END", "THE END"], self.characters["Student"]["Role"]
            return self.future_messages.pop(0), self.characters["Student"]["Role"]

        if self.last_round:

            self.conversation_ender()

            self.end = True

            self.scores.append({
                "none": ""
            })
        
        elif not user_spoke:
            
            print("Student didn't speak")

            if len(self.past_messages) > 0 and self.past_messages[-1][0] == "Student": # Student should have spoken, but did not.

                # Remove inner voice
        
                self.past_messages.pop(-1)

                print("Student should have spoken")

                # Add "..." message and regenerate

                self.past_messages.append(["Student", "..."])
                
                start_time = time.time()
                self.update_scene()
                self.logger.info('Update Scene Student Did Not Speak: %s seconds', time.time() - start_time)

                start_time = time.time()
                self.generate_conversation()
                self.logger.info('Generate Conversation Student Did Not Speak: %s seconds', time.time() - start_time)

            elif len(self.future_messages) == 0:
                print("Future window empty")

                start_time = time.time()
                self.update_scene()
                self.logger.info('Update Scene Future Window Empty: %s seconds', time.time() - start_time)

                start_time = time.time()
                self.generate_conversation()
                self.logger.info('Generate Conversation Future Window Empty: %s seconds', time.time() - start_time)

        else: # User speaks
            print("Student speaks")
            
            # Remove inner voice
        
            if len(self.past_messages) > 0 and self.past_messages[-1][0] == "Student":
                self.past_messages.pop(-1)
            
            self.past_messages.append(["Student", message])
            
            # Get message window

            current_window = [self.past_messages[-1]]

            if len(self.past_messages) > 1:

                for i in range(len(self.past_messages)-2, -1, -1):
                    if self.past_messages[i][0] == "Student":
                        break

                    current_window.insert(0, self.past_messages[i])

            # Convert to messages format

            messages = []

            for (name, message) in current_window:

                messages.append({
                    "role": "student" if name == "Student" else "assistant",
                    "content": f"{name}: {message}"
                })

            # Track goals
            start_time = time.time()
            score = self.process_conversation(messages, 
                                            aps=self.goals["addressing_prior_statement"] if "addressing_prior_statement" in self.goals else False,
                                            sot=self.goals["staying_on_topic"] if "staying_on_topic" in self.goals else False)
            
            self.scores.append({
                "message": current_window[-1][1],
                "data": score
            })
            self.logger.info('Goal Tracker User Speaks: %s seconds', time.time() - start_time)
            self.add_score_to_total(score)
            
            # Update Scene
            start_time = time.time()
            self.update_scene()
            self.logger.info('Update Scene User Speaks: %s seconds', time.time() - start_time)

            start_time = time.time()
            self.generate_conversation()
            self.logger.info('Generate Conversation User Speaks: %s seconds', time.time() - start_time)
            # Student should not speak twice in a row
            
            if self.future_messages[0][0] == "Student":
                self.future_messages.pop(0)

        # Send next message to UI and add to history

        next_message = self.future_messages.pop(0)

        self.past_messages.append(next_message)

        return next_message, self.characters["Student"]["Role"]
