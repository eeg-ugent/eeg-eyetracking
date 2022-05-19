import os, random, copy, pandas, numpy, time
from psychopy import parallel, monitors, visual, gui, data, event, core
from psychopy.iohub import launchHubServer
from psychopy.iohub.util import hideWindow, showWindow

####################SELECT THE RIGHT LAB & Mode####################
lab = 'actichamp' #'actichamp'/'biosemi'

mode = 'default' #'default'/'DemoMode' #affects nr of trials per block (50%)

ET = True #True/False #are we connecting to the eyetracker?
############################################################

#dlg box#
info =  {'Participant ID (***)': '', 'Name': '', 'Gender': ['Male','Female', 'X'], 'Age': ''}

AlreadyExists = True
while AlreadyExists: #keep asking for a new name when the data file already exists
    Dlg = gui.DlgFromDict(dictionary=info, title='N2pc Experiment') # display the gui
    FileName = os.getcwd() + '/experimental_data/' + 'n2pc_participant' + info['Participant ID (***)'] #determine the file name

    if not Dlg.OK:
        core.quit()

    if not os.path.isfile((FileName + '.csv')): #Only escape the while loop if ParticipantNr is unique
        AlreadyExists = False
    else:
        Dlg2 = gui.Dlg(title = 'Warning') #if the ParticipantNr is not unique, present a warning msg
        SuggestedParticipantNr = 0
        SuggestedFileName = FileName
        while os.path.isfile(SuggestedFileName + '.csv'): #provide a suggestion for another ParticipantNr
            SuggestedParticipantNr += 1
            SuggestedFileName = os.getcwd() + '/experimental_data/' + 'n2pc_participant' + str(SuggestedParticipantNr)

        Dlg2.addText('This ParticipantNr is in use already, please select another.\n\nParticipantNr ' +  str(SuggestedParticipantNr) + ' is still available.')
        Dlg2.show()

ParticipantName = info['Name']
info.pop('Name') #remove from info section (GDPR)

#This def is placed a bit earlier than the other defs as it is already needed for #initialize window#
def LabSpecificSettings():
    EEGPort = 0
    LabMonitor = monitors.Monitor('LabMonitor')
    if lab == 'actichamp':
        EEGPort = parallel.setPortAddress('0xCFB8')
        LabMonitor.setDistance(115)
    elif lab == 'biosemi':
        EEGPort = parallel.setPortAddress('0xCFE8')
        LabMonitor.setDistance(120)
    LabMonitor.setWidth(54)
    LabMonitor.setSizePix((1920,1080))
    LabMonitor.saveMon()
    return EEGPort, LabMonitor

#initialize window#   #this requires rather some computational resources, so best to start with this early (also holfs for ###define stimuli###)
EEGPort, LabMonitor = LabSpecificSettings()
win = visual.Window((1920,1080), fullscr = True, units='pix', allowGUI=False, colorSpace='rgb255', monitor=LabMonitor, color=[128,128,128])

#prepare the eyetracker
if ET:
    eyetracker_config = dict(name='tracker')
    eyetracker_config['model_name'] = 'EYELINK 1000 DESKTOP'
    eyetracker_config['runtime_settings'] = dict(sampling_rate=1000, track_eyes='RIGHT')
    tracker_config = {'eyetracker.hw.sr_research.eyelink.EyeTracker':eyetracker_config}

    io = launchHubServer(window = win, **tracker_config)
    tracker = io.devices.tracker

    hideWindow(win)
    result = tracker.runSetupProcedure() #If you are happy with the calibration and validation, press escape to start the actual experiment
    showWindow(win)

win.mouseVisible = False

#define stimuli#
LeftStimPos = [-250,-100] 
RightStimPos = [250,-100]
FixStim = visual.Rect(win, lineColor = [0,0,0], fillColor = None, colorSpace = 'rgb255', size = [20], pos = [0,50])

WelcomeMessage = visual.TextStim(win, text = '') #don't shorthen these lines further (are mutable objects)

BlockInstructions = visual.TextStim(win, text = '')
FeedbackMsg = BreakMsg = GoodbyeMessage = GPosMessage = visual.TextStim(win, text = '')

gaze_ok_region = visual.Rect(win, size = [150], pos = [0,50], units='pix', colorSpace='named') #needed for the gpos procedure

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

    BlockInstructions.text = 'Attend the {0} hemisphere\nIndicate whether it is on the left or right side of the {1}\nPress space to start'.format(color, attend)
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

#EEGTriggerSend#
def EEGTriggerSend(EEGTrigger):
    parallel.setData(EEGTrigger)
    core.wait(0.01)
    parallel.setData(0)    

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
    TrialList = random.choices(TrialList, k = int(len(TrialList)/2))

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
win.flip() #Without this, the first screen after the tracker set up has a black background
WelcomeMessage.text =  'Hi {}!\n\nWelcome to this experiment!\n\nYour task is to indicate the location of specific colors.\n\nIn half of the blocks you need to indicate whether this color is located left/right ON THE SCREEN, and in other blocks you need to indicate whether this color is located left/right WITHIN THE STIMULUS.\n\nYou will receive this information at the start of each block.\n\nThere are eight blocks in total.\n\nDo you have any questions?\n\nPress space to start with the experiment.\n\nGood luck!'.format(ParticipantName)
WelcomeMessage.draw()
win.flip()
EEGTriggerSend(99) #may be informative for analysis to know that an information screen has been presented prior to a trial
event.waitKeys(keyList = ['space']) #no event.clearEvents() necessary

#the actual experiment#
for BlockNr in range(len(BlockList)): #0-1-2-3-4-5-6-7

    EEGPort, LabMonitor = LabSpecificSettings()
    
    if BlockNr > 0:
        FeedbackBreakMsg(NrCorrect, len(TrialList), ParticipantName)

    NrCorrect = 0 #I needed to create NrCorrect globally (otherwise it did not function properly or UnboundLocalError in AccuracyCheck())
    attend, color = TaskInstructions(BlockList[BlockNr]) #in one line it fills attend & color and shows TaskInstructions #attend is needed for SelectEEGTrigger #color is needed for the logfile

    trials = data.TrialHandler(TrialList, nReps = 1, method = 'fullRandom')
    thisExp.addLoop(trials)

    io.clearEvents()
    tracker.setRecordingState(True)

    for trial in trials:
        rt = 0 #These lines are just some admin, but kept it prior to the win.flip() for timing reasons
        response = ''
        CorrectResponse = CorResp(trial['LeftStim'], trial['RightStim'], BlockList[BlockNr])
        EEGStimulusTrigger = SelectEEGStimulusTrigger(attend, CorrectResponse)

        gpos = tracker.getLastGazePosition()
        valid_gaze_pos = isinstance(gpos, (tuple, list))
        
        gaze_in_region = valid_gaze_pos and gaze_ok_region.contains(gpos)
        
        ReportedWaitTime = 2 #StartValue
        if not gaze_in_region:
            EEGTriggerSend(98) #Just so that one can infer from the EEG signal that this msg was shown
            while ReportedWaitTime >= 0:
                GPosMessage.text = 'Focus on the box!\n\nThe task continues automatically in {} sec'.format(round(ReportedWaitTime,1))
                GPosMessage.pos = [0,50]
                GPosMessage.draw()
                FixStim.draw() #You are doing the same as in def EmptyScreen() but now also add the msg
                win.flip()
                ReportedWaitTime -= 0.2
                core.wait(0.2)

        EmptyScreen() #To get rid of the msg

        my_clock.reset()
        PreTargetInterval = random.choice([1.0, 1.1, 1.2, 1.3, 1.4, 1.5])
        core.wait(PreTargetInterval)
            
        #The procedure that now follows is based on the demo bufferImageStim.py. This screenshot approach should lead to better timing
        #in case you want to present multiple objects on the screen simultaneously
        ImageList = [trial['LeftStim']+'.bmp', trial['RightStim']+'.bmp']
        LeftStim = visual.ImageStim(win, ImageList[0], pos = LeftStimPos)
        RightStim = visual.ImageStim(win, ImageList[1], pos = RightStimPos)

        StimList = [LeftStim, RightStim, FixStim]
        screenshot = visual.BufferImageStim(win, stim=StimList, rect=(-1, 1, 1, -1)) # rect is the screen rectangle to grab, (-1, 1, 1, -1) is whole-screen
        screenshot.draw() # draw the BufferImageStim, fast
        EEGTriggerSend(EEGStimulusTrigger)
        
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
                #gaze_ok_region.draw() #Turn this on in case you want to shortly see the accepted gaze region
                EmptyScreen()

        if rt == 0:
            accuracy = 'too_late'
            EEGResponseTrigger = SelectEEGResponseTrigger(attend, accuracy, response) #this did not take place for trials with too_late responses yet
            EEGTriggerSend(EEGResponseTrigger) #this did not take place for trials with too_late responses yet

        trials.addData('SelfLoggedData', '-->') #logic: https://discourse.psychopy.org/t/reduce-unnecessary-columns-in-data-csv/9272
        trials.addData('LocalTime_DDMMYY_HMS', str(time.localtime()[2]) + '/' + str(time.localtime()[1]) + '/' + str(time.localtime()[0]) + '_' + str(time.localtime()[3]) + ':' + str(time.localtime()[4]) + ':' + str(time.localtime()[5])) #HMS = hour min sec
        trials.addData('lab', lab)
        trials.addData('mode', mode)
        trials.addData('participant', info['Participant ID (***)'])
        trials.addData('gender', info['Gender'])
        trials.addData('age', info['Age'])
        trials.addData('BlockNr', (BlockNr + 1)) #Python starts indexing at 0
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
        thisExp.nextEntry()
        
    tracker.setRecordingState(False)

#Goodbye Screen#
Goodbye.text = 'Thanks for participating!\n\nPress space to finish'
GoodbyeMessage.draw()
win.flip()
EEGTriggerSend(99) #may be informative for analysis to know that an information screen has been presented prior to a trial
event.waitKeys(keyList = ['space']) #no event.clearEvents() necessary

win.close()
tracker.setConnectionState(False)
core.quit()