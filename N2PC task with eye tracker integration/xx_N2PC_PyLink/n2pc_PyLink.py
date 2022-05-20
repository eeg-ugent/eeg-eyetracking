import os, random, copy, pandas, numpy, time, pylink #the last is to communicate with the eyetracker
from psychopy import parallel, visual, gui, data, event, core
from EyeLinkCoreGraphicsPsychoPy import EyeLinkCoreGraphicsPsychoPy #this are functions used to run the eyetracker calibration and validation

####################SELECT THE RIGHT LAB & Mode####################
lab = 'none' #'actichamp'/'biosemi'/'none'

mode = 'DemoMode' #'default'/'DemoMode' #affects nr of trials per block (50%)

EyeTracking = False #True/False
###################################################################

#dlg box#
info =  {'Participant ID (***)': '', 'Name': '', 'Gender': ['Male','Female', 'X'], 'Age': ''}

AlreadyExists = True
while AlreadyExists: #keep asking for a new name when the data file already exists
    Dlg = gui.DlgFromDict(dictionary=info, title='N2pc Experiment') # display the gui
    FileName = os.getcwd() + '/data/' + 'n2pc_participant' + info['Participant ID (***)'] #determine the file name (os.getcwd() is where your script is saved)

    if not Dlg.OK:
        core.quit()

    if not os.path.isfile((FileName + '.csv')): #only escape the while loop if ParticipantNr is unique
        AlreadyExists = False
    else:
        Dlg2 = gui.Dlg(title = 'Warning') #if the ParticipantNr is not unique, present a warning msg
        SuggestedParticipantNr = 0
        SuggestedFileName = FileName
        while os.path.isfile(SuggestedFileName + '.csv'): #provide a suggestion for another ParticipantNr
            SuggestedParticipantNr += 1
            SuggestedFileName = os.getcwd() + '/data/' + 'n2pc_participant' + str(SuggestedParticipantNr)

        Dlg2.addText('This ParticipantNr is in use already, please select another.\n\nParticipantNr ' +  str(SuggestedParticipantNr) + ' is still available.')
        Dlg2.show()

ParticipantName = info['Name']
info.pop('Name') #remove from info section (GDPR)

#initialize window#
win = visual.Window(fullscr=True, color = numpy.repeat(-0.3961, 3), colorSpace = 'rgb', units = 'pix')
win.mouseVisible = False

#define stimuli#
LeftStimPos = [-270, -50]
RightStimPos = [270, -50]
TargetStimSize = 30
FixStim = visual.Rect(win, lineColor = [-1,-1,-1], colorSpace = 'rgb', size = 20, pos = [0, 50])

WelcomeMessage = FeedbackMsg = BreakMsg = GoodbyeMessage = ETMsg = visual.TextStim(win, text = '', height = 30) #don't shorthen these lines further (are mutable objects)
BlockInstructions = visual.TextStim(win, text = '', height = 35)

#EEGTriggerSend#
def EEGTriggerSend(EEGTrigger):
    if not lab == 'none':
        parallel.setData(EEGTrigger)
        core.wait(0.01)
        parallel.setData(0)

#EmptyScreen#
def EmptyScreen():
    FixStim.draw()
    win.flip()

#BlockInstructions#
def TaskInstructions(BlockNr_var): #if changing BlockNr_var for BlockNr: TypeError: list indices must be integers or slices, not str
    color = BlockList[BlockNr].split('d')[1][0:6]
    color = color.split('_', 1)[0].upper()
    if color == 'RE': #you need the if-statement because of 'GREEN'
        color = color.replace('RE','RED') #you need to do this because you splitted on 'd' earlier
    attend = BlockList[BlockNr][-6:].upper()
    
    BlockInstructions.text = 'Attend the {0} hemisphere\n\nIndicate whether it is on the left or right side of the {1}\n\nPress space to start'.format(color, attend)
    BlockInstructions.color = color
    BlockInstructions.draw()
    win.flip()
    EEGTriggerSend(99) #may be informative for analysis to know that an information screen has been presented prior to a trial
    event.waitKeys(keyList = ['space'])
    return attend, color #attend is needed for def SelectEEGTrigger #color is needed for logfile

#Feedback/Break events#
def FeedbackBreakMsg(NrCorrect, TrialListLength, ParticipantName):
        FeedbackMsg.text = 'You responsed correct to {}% of the trials in this block.\n\nPress space to continue.'.format(int((NrCorrect/TrialListLength)*100))
        FeedbackMsg.draw()
        win.flip()
        EEGTriggerSend(99) #may be informative for analysis to know that an information screen has been presented prior to a trial
        event.waitKeys(keyList = ['space']) #no event.clearEvents() necessary
        BreakMsg.text = 'You can take a break now, {}.\n\nPress space to continue'.format(ParticipantName)
        BreakMsg.draw()
        win.flip()
        EEGTriggerSend(99) #may be informative for analysis to know that an information screen has been presented prior to a trial
        event.waitKeys(keyList = ['space']) #no event.clearEvents() necessary

#CorrectResponse#
def CorResp(LeftStim_var, RightStim_var, BlockNr_var):
    CorrectResponse = 'right' #will be overwritten if needed
    if (BlockList[BlockNr] == 'AttendBlue_OnScreen' and trial['LeftStim'].find('B') > -1) or \
    (BlockList[BlockNr] == 'AttendBlue_WithinObject' and (trial['LeftStim'].find('B') == 0 or trial['RightStim'].find('B') == 0)) or \
    (BlockList[BlockNr] == 'AttendBlue_WithinObject' and (trial['LeftStim'].find('B') == 0 or trial['RightStim'].find('B') == 0)) or \
    (BlockList[BlockNr] == 'AttendGreen_OnScreen' and trial['LeftStim'].find('G') > -1) or \
    (BlockList[BlockNr] == 'AttendGreen_WithinObject' and (trial['LeftStim'].find('G') == 0 or trial['RightStim'].find('G') == 0)) or \
    (BlockList[BlockNr] == 'AttendRed_OnScreen' and trial['LeftStim'].find('R') > -1) or \
    (BlockList[BlockNr] == 'AttendRed_WithinObject' and (trial['LeftStim'].find('R') == 0 or trial['RightStim'].find('R') == 0)) or \
    (BlockList[BlockNr] == 'AttendYellow_OnScreen' and trial['LeftStim'].find('Y') > -1) or \
    (BlockList[BlockNr] == 'AttendYellow_WithinObject' and (trial['LeftStim'].find('Y') == 0 or trial['RightStim'].find('Y') == 0)):
        CorrectResponse = 'left'
    return CorrectResponse

#AccuracyCheck#
def AccuracyCheck(response, CorrectResponse, TrialNr, NrCorrect):
    if response == CorrectResponse:
        accuracy = 'correct'
    elif not response == '':
        accuracy = 'error' #of note, later in the code you will see that you don't need to define too_late here
    NrCorrect += ((response == CorrectResponse) * 1)
    return accuracy, NrCorrect

#SelectEEGStimulusTrigger#
def SelectEEGStimulusTrigger(attend, CorrectResponse):
    if attend == 'SCREEN':
        if CorrectResponse == 'left':
            EEGStimulusTrigger = 10
        else:
            EEGStimulusTrigger = 11
    else:
        if CorrectResponse == 'left':
            EEGStimulusTrigger = 12
        else:
            EEGStimulusTrigger = 13
    return EEGStimulusTrigger

#SelectEEGResponseTrigger#
def SelectEEGResponseTrigger(attend, accuracy_var, response_var): #accepts attend (repetition; no error msg such as above)
    if accuracy == 'correct':
        if response == 'left': #Nico was okay with the logic of response * accuracy
            EEGResponseTrigger = 21
        else:
            EEGResponseTrigger = 22
    elif accuracy == 'error':
        if response == 'left':
            EEGResponseTrigger = 23
        else:
            EEGResponseTrigger = 24          
    else:
            EEGResponseTrigger = 25
    if attend == 'OBJECT':
        EEGResponseTrigger += 10
    return EEGResponseTrigger  

#No def, just some basic set up for the eyetracker#
if EyeTracking:
    eyeTracker = pylink.EyeLink('100.1.1.1') #connect to the tracker using the pylink library

    FileNameET = 'n2pc_' + info['Participant ID (***)'] + '.EDF' #open datafile (max 8 characters)
    
    eyeTracker.openDataFile(FileNameET)
    eyeTracker.sendCommand("add_file_preamble_text 'N2pc Experiment'") #add personalized data file header (preamble text)
    
    genv = EyeLinkCoreGraphicsPsychoPy(eyeTracker, win) #set up a custom graphics environment (EyeLinkCoreGraphicsPsychopy) for calibration
    pylink.openGraphicsEx(genv)
    
    eyeTracker.setOfflineMode() #put the tracker in idle mode before we change some parameters
    pylink.pumpDelay(100)
    eyeTracker.sendCommand("screen_pixel_coords = 0 0 %d %d" % (1920-1, 1080-1)) #send screen resolution to the tracker, format: (scn_w - 1, scn_h - 1) #here: 1920 x 1080!
    eyeTracker.sendMessage("DISPLAY_COORDS = 0 0 %d %d" % (1920-1, 1080-1)) #relevant only for data viewer #here: 1920 x 1080!
    eyeTracker.sendCommand("sample_rate 1000") #250, 500, 1000, or 2000 (only for EyeLink 1000 plus)
    eyeTracker.sendCommand("recording_parse_type = GAZE")
    eyeTracker.sendCommand("select_parser_configuration 0") #saccade detection thresholds: 0-> standard/coginitve, 1-> sensitive/psychophysiological
    eyeTracker.sendCommand("calibration_type = HV13") #13 point calibration (recommended for head free remote mode)

    ETMsg.text = 'Press ENTER to set up the tracker\n' #show calibration message
    ETMsg.draw()
    win.flip()

    eyeTracker.doTrackerSetup() #calibrate the tracker #once you are happy with the calibration and validation (!), you are ready to run the experiment. 

    pylink.closeGraphics(genv)

#No def, just setting up the EEG
if lab == 'actichamp':
    parallel.setPortAddress('0xCFB8')
elif lab == 'biosemi':
    parallel.setPortAddress('0xCFE8')

#TrialList admin#
TrialList = [   #You cannot shorten this with the createFactorialTrialList() function! In that case the same colors can occur within a trial
{'LeftStim': 'BG', 'RightStim': 'RY'},{'LeftStim': 'BG', 'RightStim': 'YR'},{'LeftStim': 'BR', 'RightStim': 'GY'},{'LeftStim': 'BR', 'RightStim': 'YG'},
{'LeftStim': 'BY', 'RightStim': 'GR'},{'LeftStim': 'BY', 'RightStim': 'RG'},{'LeftStim': 'GB', 'RightStim': 'RY'},{'LeftStim': 'GB', 'RightStim': 'YR'},
{'LeftStim': 'GR', 'RightStim': 'BY'},{'LeftStim': 'GR', 'RightStim': 'YB'},{'LeftStim': 'GY', 'RightStim': 'BR'},{'LeftStim': 'GY', 'RightStim': 'RB'},
{'LeftStim': 'RB', 'RightStim': 'GY'},{'LeftStim': 'RB', 'RightStim': 'YG'},{'LeftStim': 'RG', 'RightStim': 'BY'},{'LeftStim': 'RG', 'RightStim': 'YB'},
{'LeftStim': 'RY', 'RightStim': 'BG'},{'LeftStim': 'RY', 'RightStim': 'GB'},{'LeftStim': 'YB', 'RightStim': 'GR'},{'LeftStim': 'YB', 'RightStim': 'RG'},
{'LeftStim': 'YG', 'RightStim': 'BR'},{'LeftStim': 'YG', 'RightStim': 'RB'},{'LeftStim': 'YR', 'RightStim': 'BG'},{'LeftStim': 'YR', 'RightStim': 'GB'}]

for TrialList_var in range(4):
    globals()['TrialList' + str((chr((TrialList_var+65))))] = copy.deepcopy(TrialList)
        
for trial_var in range(len(TrialList)):
    TrialListA[trial_var].update({'duration': 0.7}) #I tried to condense this code by looping but you easily get the warning: AttributeError: 'list' object has no attribute 'update'
    TrialListB[trial_var].update({'duration': 0.8})
    TrialListC[trial_var].update({'duration': 0.9})
    TrialListD[trial_var].update({'duration': 1.0})

    TrialList = TrialListA + TrialListB + TrialListC + TrialListD

if mode == 'DemoMode':
    #TrialList = random.choices(TrialList, k = int(len(TrialList)/2))
    TrialList = random.choices(TrialList, k = int(len(TrialList)/24)) #just for now

#For pilotting purposes only - Cross Tabs#
#dataFrame = pandas.DataFrame.from_dict(TrialList) #To inspect the TrialList
#print(pandas.crosstab(dataFrame.LeftStim, dataFrame.RightStim))

#BlockList admin#
BlockList = ['AttendBlue_OnScreen','AttendBlue_WithinObject','AttendGreen_OnScreen','AttendGreen_WithinObject','AttendRed_OnScreen','AttendRed_WithinObject','AttendYellow_OnScreen','AttendYellow_WithinObject']
random.shuffle(BlockList) #of note, the instructions need to be centered (is not the case in the lab)

#ExperimentHandler#
thisExp = data.ExperimentHandler(dataFileName = FileName)
my_clock = core.Clock() #define my_clock

#Welcome instructions#
WelcomeMessage.text =  'Hi {}!\n\nWelcome to this experiment!\n\nYour task is to indicate the location of specific colors.\n\nIn half of the blocks you need to indicate whether this color is located left/right ON THE SCREEN, and in other blocks you need to indicate whether this color is located left/right WITHIN THE STIMULUS.\n\nYou will receive this information at the start of each block.\n\nThere are eight blocks in total.\n\nDo you have any questions?\n\nPress space to start with the experiment.\n\nGood luck!'.format(ParticipantName)
WelcomeMessage.draw()
win.flip()
EEGTriggerSend(99) #may be informative for analysis to know that an information screen has been presented prior to a trial
event.waitKeys(keyList = ['space']) #no event.clearEvents() necessary

#the actual experiment#
for BlockNr in range(2):#range(len(BlockList)): #0-1-2-3-4-5-6-7 #just for now
    
    if BlockNr > 0:
        FeedbackBreakMsg(NrCorrect, len(TrialList), ParticipantName)

    if EyeTracking:
        eyeTracker.setOfflineMode() #this is called before start_recording() to make sure the eye tracker has enough time to switch modes (to start recording)
        pylink.pumpDelay(100)
        eyeTracker.startRecording(1,1,1,1) #starts the EyeLink tracker recording, sets up link for data reception if enabled. The 1,1,1,1 just has to with whether samples and events etcetera needs to be written to EDF file. Recording needs to be started for each block
        pylink.pumpDelay(100) #wait for 100 ms to cache some samples

    NrCorrect = 0 #I needed to create NrCorrect globally (otherwise it did not function properly or UnboundLocalError in AccuracyCheck())
    attend, color = TaskInstructions(BlockList[BlockNr]) #in one line it fills attend & color and shows TaskInstructions #attend is needed for SelectEEGTrigger #color is needed for the logfile

    trials = data.TrialHandler(TrialList, nReps = 1, method = 'fullRandom')
    thisExp.addLoop(trials)

    for trial in trials:
        
        if EyeTracking:
            eyeTracker.sendMessage('BLOCKID %d' % (BlockNr + 1))
            eyeTracker.sendMessage('TRIALID %d' % (trials.thisTrialN + 1)) #send a message ("TRIALID") to mark the start of a trial
            eyeTracker.sendCommand("record_status_message 'attend %s color %s block %s trial %s'" % (attend, color, (BlockNr + 1), (trials.thisTrialN + 1))) #to show on the host pc the current task, block nr and trial nr #+1 because Python starts at 0

        rt = 0 #the upcoming lines are just some admin
        response = ''
        CorrectResponse = CorResp(trial['LeftStim'], trial['RightStim'], BlockList[BlockNr])
        EEGStimulusTrigger = SelectEEGStimulusTrigger(attend, CorrectResponse)

        EmptyScreen()

        PreTargetInterval = random.choice([1.0, 1.1, 1.2, 1.3, 1.4, 1.5])
        core.wait(PreTargetInterval)

        ImageList = [trial['LeftStim']+'.bmp', trial['RightStim']+'.bmp'] #The procedure that now follows is based on the demo bufferImageStim.py. This screenshot approach should lead to better timing in case you want to present multiple objects on the screen simultaneously
        LeftStim = visual.SimpleImageStim(win, ImageList[0], pos = LeftStimPos)
        RightStim = visual.SimpleImageStim(win, ImageList[1], pos = RightStimPos)
        LeftStim.Size = RightStim.Size = TargetStimSize
        
        StimList = [LeftStim, RightStim, FixStim]
        screenshot = visual.BufferImageStim(win, stim=StimList, rect=(-1, 1, 1, -1)) # rect is the screen rectangle to grab, (-1, 1, 1, -1) is whole-screen
        screenshot.draw() # draw the BufferImageStim, fast
        EEGTriggerSend(EEGStimulusTrigger)

        if EyeTracking:
            eyeTracker.sendMessage('TrialInfo %s' % ImageList)

        event.clearEvents(eventType = 'keyboard') #necessary in combination with event.getKeys()

        win.flip()
        my_clock.reset() #resetting here leads to the least amount of measurement errors (only onset is slightly off [0.5 refresh time])
        while my_clock.getTime() <= 2.0:
            keys = event.getKeys(keyList = ['left','right','escape'])
            if len(keys) == 1 and rt == 0: #should only enter this the very moment a response was registered
                rt = int((my_clock.getTime() * 1000))
                response = keys[0]
                accuracy, NrCorrect = AccuracyCheck(response, CorrectResponse, trials.thisTrialN, NrCorrect)
                EEGResponseTrigger = SelectEEGResponseTrigger(attend, accuracy, response) #make lab specific: if biosemi code == else == . give in lab at beginning, so right port I mean
                EEGTriggerSend(EEGResponseTrigger)
                if response == 'escape':
                    core.quit()
            if my_clock.getTime() > trial['duration']:
                EmptyScreen()

        if rt == 0:
            accuracy = 'too_late'
            EEGResponseTrigger = SelectEEGResponseTrigger(attend, accuracy, response) #this did not take place for trials with too_late responses yet
            EEGTriggerSend(EEGResponseTrigger) #this did not take place for trials with too_late responses yet

        if EyeTracking:
            eyeTracker.sendMessage('RT %d' % rt)
            eyeTracker.sendMessage('accuracy %s' % accuracy)

        trials.addData('SelfLoggedData', '-->') #logic: https://discourse.psychopy.org/t/reduce-unnecessary-columns-in-data-csv/9272
        trials.addData('LocalTime_DDMMYY_HMS', str(time.localtime()[2]) + '/' + str(time.localtime()[1]) + '/' + str(time.localtime()[0]) + '_' + str(time.localtime()[3]) + ':' + str(time.localtime()[4]) + ':' + str(time.localtime()[5])) #HMS = hour min sec
        trials.addData('lab', lab)
        trials.addData('mode', mode)
        trials.addData('participant', info['Participant ID (***)'])
        trials.addData('gender', info['Gender'])
        trials.addData('age', info['Age'])
        trials.addData('BlockNr', (BlockNr + 1)) #Python starts indexing at 0
        trials.addData('TrialNr', (trials.thisTrialN +1)) #Python starts indexing at 0
        trials.addData('WhatToAttend', attend.lower())
        trials.addData('ColorToAttend', color.lower())
        trials.addData('PreTargetInterval', PreTargetInterval)
        trials.addData('LeftStim', trial['LeftStim'])
        trials.addData('RightStim', trial['RightStim'])
        trials.addData('TargetDuration', trial['duration'])
        trials.addData('response', response)
        trials.addData('CorrectResponse', CorrectResponse)
        trials.addData('RT', rt)
        trials.addData('accuracy', accuracy)
        trials.addData('EEGStimulusTrigger', EEGStimulusTrigger) #for pilotting, I would just leave this in also for lab = 'none'
        trials.addData('EEGResponseTrigger', EEGResponseTrigger)

        if EyeTracking:
            eyeTracker.sendMessage('TRIAL_END') #this marks the end of the trial

        thisExp.nextEntry()

    if EyeTracking:
        eyeTracker.stopRecording() #this is typically done for each block

if EyeTracking:
    eyeTracker.setOfflineMode()
    pylink.pumpDelay(100)
    eyeTracker.closeDataFile() #close the EDF data file

    ETMsg.text = 'EDF data is transfering from EyeLink Host PC'
    ETMsg.draw()
    win.flip()
    pylink.pumpDelay(500)

    eyeTracker.receiveDataFile(FileNameET, os.getcwd() + '/data/' + FileNameET) #get the EDF data
    #of note, if you want to convert the EDF to ASC files, go to Start Menu -> SR Research -> Visual EDF2ASC (if downloading Data Viewer, you get this program as well)
    
    eyeTracker.close() #close the link to the tracker

#Goodbye Screen#
GoodbyeMessage.text = 'Thanks for participating!\n\nPress space to finish'
GoodbyeMessage.draw()
win.flip()
EEGTriggerSend(99) #may be informative for analysis to know that an information screen has been presented prior to a trial
event.waitKeys(keyList = ['space']) #no event.clearEvents() necessary

win.close()
core.quit()