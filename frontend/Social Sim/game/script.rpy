init python:
    import requests

    # Backgrounds

    renpy.image("bg_bus", "bg_bus.jpeg")
    renpy.image("bg_cafeteria", "bg_cafeteria.jpg")
    renpy.image("bg_classroom", "bg_classroom.jpeg")
    renpy.image("bg_coffee_shop", "bg_coffee_shop.jpg")
    renpy.image("bg_street", "bg_street.jpg")
    renpy.image("bg_train", "bg_train.jpg")
    renpy.image("bg_whiteboard", "bg_whiteboard.jpg")

    # Characters

    renpy.image("c_male_1", "c_male_1.png")
    renpy.image("c_male_2", "c_male_2.png")
    renpy.image("c_male_3", "c_male_3.png")
    renpy.image("c_male_4", "c_male_4.png")

    renpy.image("c_female_1", "c_female_1.png")
    renpy.image("c_female_2", "c_female_2.png")
    renpy.image("c_female_3", "c_female_3.png")
    renpy.image("c_female_4", "c_female_4.png")

    # Global variables

    social_skill = ""

    goals_to_track = {
        "addressing_prior_statement": False,
        "staying_on_topic": False
    }

    background = "bg_park"
    character_images = {}

    inner_voice = ""
    user_spoke = False
    user_input = ""

    scores = []


label start:

    jump get_scene_input


label get_scene_input:

    # Collect user input for scene setup

    show bg_whiteboard

    menu:

        "Select the social skill you wish to learn"

        "Participating in a group conversation":
            $ social_skill = "Participating in a group conversation"

        "Initiating a conversation with a stranger":
            $ social_skill = "Initiating a conversation with a stranger"

    menu:

        "Would you like to track whether the student addresses prior statements?"

        "Yes":
            $ goals_to_track["addressing_prior_statement"] = True
        "No":
            $ goals_to_track["addressing_prior_statement"] = False

    menu:

        "Would you like to track whether the student stays on topic?"

        "Yes":
            $ goals_to_track["staying_on_topic"] = True
        "No":
            $ goals_to_track["staying_on_topic"] = False

    jump situation_overview


label situation_overview:

    # Set up scene

    python:
    
        try:
            response = requests.post('http://localhost:8000/scene/setup', json={"social_skill": social_skill, "goals": goals_to_track}, timeout=100)
            if response.status_code == 200:
                data = response.json()  # Parse the JSON response
            else:
                renpy.say(who=None, what="Scene Setup Failed :(")
                renpy.jump("end_screen")
        except:
            renpy.say(who=None, what="Scene Setup Failed :(")
            renpy.jump("end_screen")
                
        background = data["background"]
        renpy.show(background)

        scenario_text = social_skill
        event_text = data["location"]

        renpy.show_screen("scenario_text")
        renpy.show_screen("event_text")

        renpy.display_menu([("Scene Overview", False), (data["overview"], True)])

        renpy.display_menu([("Location", False), (data["location"], True)])

        renpy.say(who=None, what="Here are the characters involved in the scene")

        characters = data["characters"]
        character_images = data["character_images"]

        for name in data["characters"]:

            if name == "Student":
                continue

            # Display character image

            renpy.show(character_images[name], at_list=(center, right))

            # Display character details

            renpy.say(who=None, what=f"This is {name}.")
            renpy.say(who=None, what=characters[name]["Personality"])
            renpy.say(who=None, what=characters[name]["Role"])

            renpy.hide(character_images[name])
  
        renpy.say(who=None, what="{w=0.5}Now let's get started...")

        # Show all characters

        pos = 0
        for (name, asset) in character_images.items():
            if pos == 0:
                renpy.show(asset, at_list=(center, right))
            elif pos == 1:
                renpy.show(asset, at_list=(center, left))
            elif pos == 2:
                renpy.show(asset, at_list=(center, center))
            pos += 1

        narration = [line.strip() + "." for line in data["narration"].split(".") if line.strip() != ""]

        for line in narration:
            renpy.say(who=None, what=line)

        renpy.jump("first_user_input")


label first_user_input:

    python:

        # User has to minimally enter the first input

        user_input = ""
        inner_voice = "Start the scene by saying something."

        renpy.call("get_user_input")


label conversation:

    python:

        while True:
 
            # Determine if user said something or not

            if user_spoke:

                renpy.say(who="Student", what=user_input)

                if user_input == "end":
                    renpy.hide_screen("scenario_text")
                    renpy.hide_screen("event_text")
                    renpy.hide("c_male_teen_1")
                    renpy.scene()
                    renpy.jump("end_screen")
            else:
                user_input = ""

            renpy.show_screen("raise_hand_button")

            message = ["Error", "Something went wrong :("]
            score = None

            try:
                response = requests.post('http://localhost:8000/scene/interact', json={"user_spoke": user_spoke, "message": user_input if user_spoke else ""}, timeout=100)
                if response.status_code == 200:
                    data = response.json()  # Parse the JSON response
                    message = data['message']
                    score = data['score']
                else:
                    renpy.say(who=None, what="Scene Interaction Failed :(")
                    renpy.jump("end_screen")
            except:
                renpy.say(who=None, what="Scene Interaction Failed :(")
                renpy.jump("end_screen")
                
            if score:
                scores.append(score)
            
            name, message_text = message

            if name == "END":
                renpy.jump("end_screen")

            elif name == "Student":

                # Inner Voice prompting
                #inner_voice = f"You could say something like: {message_text}"
                inner_voice = data["inner_voice"]

                renpy.say(who=None, what="(You might wanna say something here...)")

            else:

                # In-line character dialogue
                inner_voice = ""
                renpy.say(who=(message[0] if message[0] != "Error" else None), what=message[1])

            renpy.show_screen("raise_hand_button")
            user_spoke = False


label get_user_input:

    python:

        renpy.hide_screen("raise_hand_button")

        if len(inner_voice.strip()) == 0:
            inner_voice = "You are doing great! What do you think you could say here?"
        
        renpy.display_menu([(inner_voice, False)], interact=False)

        prompt = "What would you like to say?"
            
        user_spoke = True
        user_input  = ""

        while user_input == "":
            user_input = renpy.input(prompt)
            if user_input and user_input != "":
                user_input = user_input.strip()

        renpy.call_in_new_context("conversation")


label end_screen:

    python:
        renpy.hide_screen("raise_hand_button")

    "THE END"
    return
    #python:
        #renpy.show_screen("performance")
    return
