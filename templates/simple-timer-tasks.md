# Simple Countdown Timer
A minimal vanilla HTML/JS countdown timer app for small models.

## Task 1: Create HTML structure
Create a file called `index.html` with:
- A div with id="display" showing "00:00"
- An input field with id="minutes" type="number" placeholder="Minutes"
- A button with id="start" text "Start"
- A button with id="reset" text "Reset"
- Basic inline CSS: center everything, large font for display (48px), nice padding

## Task 2: Add timer variables
In index.html, add a script tag at the bottom with:
- A variable `timeLeft` set to 0
- A variable `timerInterval` set to null
- A function `updateDisplay()` that formats timeLeft as MM:SS and puts it in the display div

## Task 3: Add start function
Add a function called `startTimer()` that:
- Gets the value from the minutes input
- Multiplies by 60 to get seconds and stores in timeLeft
- Calls updateDisplay()
- Uses setInterval to decrease timeLeft by 1 every second and call updateDisplay()
- Stops when timeLeft reaches 0

## Task 4: Add reset function
Add a function called `resetTimer()` that:
- Clears the interval using clearInterval(timerInterval)
- Sets timeLeft to 0
- Calls updateDisplay()
- Clears the minutes input field

## Task 5: Connect buttons
Add event listeners:
- start button onclick calls startTimer()
- reset button onclick calls resetTimer()

## Task 6: Add alarm sound
When timer reaches 0:
- Change the display background color to red
- Use alert("Time is up!") to notify the user
- Then call resetTimer()
