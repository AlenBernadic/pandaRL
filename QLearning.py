from setup import powerGrid_ieee2
import pandas as pd
import numpy as np
import math
import pickle
import os
import matplotlib.pyplot as plt
import copy
import statistics as stat
from datetime import datetime

# Q-learning class including constructor, trainingand testing.
class qLearning:
    def __init__(self, learningRate, decayRate, numOfEpisodes, stepsPerEpisode, epsilon ,annealingConstant, annealAfter, checkpoint=''):
        # Intervals which discretizes measurements into state representation
        #self.voltageRanges=['<0.75','0.75-0-79','0.8-0-84','0.85-0.89','0.9-0.94','0.95-0.99','1-1.04','1.05-1.09','1.1-1.14','1.15-1.19','1.2-1.24','>=1.25'];
        self.voltageRanges_2=['<0.85','0.85-0.874','0.875-0.899','0.9-0.924','0.925-0-949','0.95-0.974','0.975.0.999','1-1.024','1.025-1.049','1.05-1.074','1.075-1.1','>=1.1'];
        self.loadingPercentRange=['0-9','10-19','20-29','30-39','40-49','50-59','60-69','70-79','80-89','90-99','100-109','110-119','120-129','130-139','140-149','150 and above'];
        self.statesLev1 = ['v_' + x + '_l_' + y for x in self.voltageRanges_2 for y in self.loadingPercentRange]
        self.states=['s1:' + x + ';s2:' + y +';' for x in self.statesLev1 for y in self.statesLev1]

        # initialise environment
        self.env_2bus=powerGrid_ieee2('qlearning');

        # Possible actions to take, combinations of v_ref into cobinations of lp_ref
        self.actions=['v_ref:'+str(x)+';lp_ref:'+str(y) for x in self.env_2bus.actionSpace['v_ref_pu'] for y in self.env_2bus.actionSpace['lp_ref']]

        # Check if pickle file with current hyperparams exist
        self.checkPointName='pickles_qlearning\pickled_q_table_lr'+str(learningRate)+'dr'+str(decayRate)+'noe'+str(numOfEpisodes)+'spe'+str(stepsPerEpisode)+'e'+str(epsilon)+'ac'+str(annealingConstant)+'aa'+str(annealAfter)+'.pkl';
        if os.path.isfile(self.checkPointName) or checkpoint!='':
            print('loading data from checkpoint')
            # Load Qtable from pickle file
            with open(self.checkPointName if os.path.isfile(self.checkPointName) else checkpoint, 'rb') as pickle_file:
                data = pickle.load(pickle_file)
                self.epsilon = data['e'] if os.path.isfile(self.checkPointName) else epsilon;
                self.q_table = data['q_table'];
                self.allRewards = data['allRewards'] if os.path.isfile(self.checkPointName) else [];
        else: # create new Qtable
            self.q_table = pd.DataFrame(0, index=np.arange(len(self.actions)), columns=self.states);
            self.epsilon = epsilon
            self.allRewards = [];
        self.numOfEpisodes = numOfEpisodes
        self.annealingRate = annealingConstant
        self.numOfSteps = stepsPerEpisode
        self.learningRate = learningRate
        self.decayRate = decayRate
        self.annealAfter=annealAfter

    ## Old version saved for ref. Use getStateFromMeasurements_2
    def getStateFromMeasurements(self, voltageLoadingPercentArray):
        res='';
        count=1;
        for voltageLoadingPercent in voltageLoadingPercentArray:
            voltage=voltageLoadingPercent[0];
            loadingPercent=voltageLoadingPercent[1];
            v_ind = (math.floor(round(voltage * 100) / 5) - 14);
            v_ind = v_ind if v_ind >=0 else 0;
            v_ind = v_ind if v_ind < len(self.voltageRanges) else len(self.voltageRanges)-1;
            l_ind = (math.floor(round(loadingPercent)/10));
            l_ind = l_ind if l_ind < len(self.loadingPercentRange) else len(self.loadingPercentRange)-1;
            res=res + 's'+str(count)+':v_' + self.voltageRanges[v_ind] + '_l_' + self.loadingPercentRange[l_ind]+';';
            count+=1
        return res;

    ## Return state representation from measurements
    def getStateFromMeasurements_2(self, voltageLoadingPercentArray):
        res = '';
        count = 1;
        for voltageLoadingPercent in voltageLoadingPercentArray:
            voltage = voltageLoadingPercent[0];
            loadingPercent = voltageLoadingPercent[1];
            v_ind = (math.floor(round(voltage * 100) / 2.5) - 33);
            v_ind = v_ind if v_ind >= 0 else 0;
            v_ind = v_ind if v_ind < len(self.voltageRanges_2) else len(self.voltageRanges_2) - 1;
            l_ind = (math.floor(round(loadingPercent) / 10));
            l_ind = l_ind if l_ind < len(self.loadingPercentRange) else len(self.loadingPercentRange) - 1;
            res = res + 's' + str(count) + ':v_' + self.voltageRanges_2[v_ind] + '_l_' + self.loadingPercentRange[
                l_ind] + ';';
            count += 1
        return res;

    ## Returns values for v_ref and lp_ref from index in action array
    def getActionFromIndex(self, ind):
        actionString=self.actions[ind];
        actionStringSplitted=actionString.split(';');
        voltage = actionStringSplitted[0].split(':')[1];
        loadingPercent = actionStringSplitted[1].split(':')[1];
        return((int(loadingPercent),float(voltage) ));

    ## Test and plot accumulated reward given a number of episodes and steps per episode
    ## Also prints number of unique states visited
    def test(self, episodes, numOfStepsPerEpisode):
        self.env_2bus.setMode('test')
        rewards=[]
        count=0;
        ul=self.numOfSteps;
        for i in self.q_table:
           if len(self.q_table[i].unique()) > 1:
               #print(i);
               count+=1;
        print('Number of Unique States Visited: '+ str(count));
          # print(q_table[i].min())
        for j in range(0,episodes):
            self.env_2bus.reset();
            currentMeasurements = self.env_2bus.getCurrentState();
            oldMeasurements=currentMeasurements;
            rewardForEp=[];
            for i in range(0,numOfStepsPerEpisode):
                currentState = self.getStateFromMeasurements_2([oldMeasurements,currentMeasurements]);
                actionIndex = self.q_table[currentState].idxmax();
                #print(q_table[currentState].unique())
                action = self.getActionFromIndex(actionIndex);
                oldMeasurements=currentMeasurements;
                currentMeasurements, reward, done, _ = self.env_2bus.takeAction(action[0], action[1]);
                # if i == ul-1:
                #     oldMeasurements = currentMeasurements;
                #     ul+=self.numOfSteps;
                rewardForEp.append(reward);
                #print(self.env_2bus.net.res_bus.vm_pu)
                #print(self.env_2bus.net.res_line)
            rewards.append(sum(rewardForEp));
            #print(sum(rewards))
        plt.scatter(list(range(0, len(rewards))), rewards)
        plt.show();

    ## Compare policy with testing all actions iteratively. (Very expensive)
    def testAllActions(self, numOfSteps):
        allRewards=[];
        greedyReward=0;

        self.env_2bus.reset();
        #print(env_2bus.net.load)

        currentMeasurements = self.env_2bus.getCurrentState();
        oldMeasurements=currentMeasurements;
        for j in range(0,numOfSteps):
            print('Step: ' + str(j))
            print('Measurements before taking action ')
            print('v: '+str(self.env_2bus.net.res_bus.vm_pu[1])+'; lp deviation:  '+str(np.std(self.env_2bus.net.res_line.loading_percent)))
            #print(self.env_2bus.net.res_line.loading_percent[1])
            #print(self.env_2bus.net.res_line.loading_percent[0])
            #print(np.std(self.env_2bus.net.res_line.loading_percent))
            rewards = [];
            compensation = []
            measurements = []
            self.env_2bus.setMode('test')
            # Try all actions and store rewards in array
            for i in range(0, len(self.actions)):
                copyNetwork=copy.deepcopy(self.env_2bus);
                #measurements.append({'v_meas': copyNetwork.net.res_bus.vm_pu[1], 'lp_meas': copyNetwork.net.res_line.loading_percent[1]})
                #copyNetwork.runEnv()
                #print(copyNetwork.net.load)
                #copyNw=powerGrid_ieee2();
                #copyNw.stateIndex=env_2bus.stateIndex; #Copying stateindex, but load is still radomized from init() to different value than env_2bus
                #copyNw.scaleLoadAndPowerValue(copyNw.stateIndex, -1);
                #copyNw.runEnv()
                #print(copyNw.net.load)
                action = self.getActionFromIndex(i);
                nextStateMeasurements, reward, done, _ = copyNetwork.takeAction(action[0], action[1]);
                rewards.append(reward);
                compensation.append({'k':copyNetwork.k_old,'q': copyNetwork.q_old})
                measurements.append({'v_bus1': copyNetwork.net.res_bus.vm_pu[1], 'lp_std': np.std(copyNetwork.net.res_line.loading_percent)})
            allRewards.append(rewards)
            currentState = self.getStateFromMeasurements_2([oldMeasurements, currentMeasurements]);
            actionIndex = self.q_table[currentState].idxmax();
            action = self.getActionFromIndex(actionIndex);
            oldMeasurements = currentMeasurements;
            currentMeasurements, reward, done, _ = self.env_2bus.takeAction(action[0], action[1]);
            print('algorithm reward: '+str(reward));
            print(compensation[actionIndex])
            print('max possible reward from all actions: '+str(max(rewards)));
            print(compensation[rewards.index(max(rewards))])
            print('Measurements after taking algorithm best action ')
            print(measurements[actionIndex])
            greedyReward+=rewards[actionIndex]
        #action = getActionFromIndex(actionIndex);
        #nextStateMeasurements2, reward2, done2, _ = env_2bus.takeAction(action[0], action[1]);
        #print(env_2bus.stateIndex-1)
        #print(reward2);
        #print(rewards)
        print('Reward From Greedy Actions for entire episode using algorithm: '+str(greedyReward))

        print('Max Reward Possible by acting greedily at each step:'+str(sum([max(x) for x in allRewards])))

    ## Compare Qlearning policy with another wrt reward
    def compareWith(self, models, episodes, numOfStepsPerEpisode):
        rewards = [[]];
        for j in range(0, episodes):
            self.env_2bus.reset();
            self.env_2bus.setMode('test')
            for i in models:
                oldIndex=i.env_2bus.stateIndex;
                i.env_2bus.stateIndex=self.env_2bus.stateIndex;
                i.env_2bus.net.switch.at[0, 'closed'] = False
                i.env_2bus.net.switch.at[1, 'closed'] = True
                i.env_2bus.k_old = 0;
                i.env_2bus.q_old = 0;
                i.env_2bus.scaleLoadAndPowerValue(self.env_2bus.stateIndex);
                i.env_2bus.runEnv(False);
                if len(rewards) < len(models)+1:
                    rewards.append([]);

            for k in range(0,len(models)+1):
                currentModel=self if k == len(models) else models[k];
                currentMeasurements = currentModel.env_2bus.getCurrentState();
                oldMeasurements = currentMeasurements;
                rewardForEp = 0;
                for i in range(0, numOfStepsPerEpisode):
                    currentState = currentModel.getStateFromMeasurements_2([oldMeasurements, currentMeasurements]);
                    actionIndex = currentModel.q_table[currentState].idxmax();
                    # print(q_table[currentState].unique())
                    action = currentModel.getActionFromIndex(actionIndex);
                    oldMeasurements = currentMeasurements;
                    currentMeasurements, reward, done, _ = currentModel.env_2bus.takeAction(action[0], action[1]);
                    rewardForEp += reward;
                    # print(self.env_2bus.net.res_bus.vm_pu)
                    # print(self.env_2bus.net.res_line)
                rewards[k].append(rewardForEp);
            # print(sum(rewards))
        i_list = list(range(0, len(rewards[0])))
        fig, ax1 = plt.subplots()
        color = 'tab:blue'
        ax1.set_xlabel('Episodes')
        ax1.set_ylabel('Reward', color=color)
        ax1.plot(i_list, rewards[0], color=color)
        ax1.plot(i_list, rewards[1], color='g')
        #ax1.plot(i_list, v_RLFACTS, color='r')
        ax1.legend([models[0].checkPointName, self.checkPointName], loc=2)
        #ax2 = ax1.twinx()

        #plt.plot(list(range(0, len(rewards[0]))), rewards[0],color="red")
        #plt.plot(list(range(0, len(rewards[1]))), rewards[1],  color="green")
        plt.show();

    ## Train algorithm
    def train(self):
        self.env_2bus.setMode('train')
        print('epsilon: ' + str(self.epsilon))
        print('Has already been  trained for following num of episodes: ' + str(len(self.allRewards)))
        noe=self.numOfEpisodes - len(self.allRewards)
        for i in range(0,noe):
            accumulatedReward=0;
            self.env_2bus.reset();
            currentMeasurements = self.env_2bus.getCurrentState();
            oldMeasurements = currentMeasurements; # current and old same first step of episode
            for j in range(0,self.numOfSteps):
                epsComp = np.random.random();
                currentState=self.getStateFromMeasurements_2([oldMeasurements,currentMeasurements]);
                if epsComp <= self.epsilon:
                        # Exploration Part
                     actionIndex = np.random.choice(len(self.actions), 1)[0]
                else:
                        # Greedy Approach
                    actionIndex=self.q_table[currentState].idxmax();
                action = self.getActionFromIndex(actionIndex);
                oldMeasurements=currentMeasurements;
                currentMeasurements, reward, done, _ = self.env_2bus.takeAction(action[0],action[1])
                accumulatedReward += reward;
                if done:
                    nextStateMaxQValue = 0;
                else:
                    nextState = self.getStateFromMeasurements_2([oldMeasurements,currentMeasurements]);
                    nextStateMaxQValue=self.q_table[nextState].max();
                    # Update Qvalue for given action:
                self.q_table.iloc[actionIndex,self.states.index(currentState)] = self.q_table[currentState][actionIndex] + self.learningRate*(reward + self.decayRate*nextStateMaxQValue - self.q_table[currentState][actionIndex])
                if done:
                    break;
            self.allRewards.append(accumulatedReward);
                # Print progress of training with last reward
            if (i+1) % self.annealAfter == 0:
                print('Episode: ' + str(len(self.allRewards)) + '; reward:' + str(accumulatedReward))
                self.epsilon=self.annealingRate*self.epsilon;
                print('saving checkpoint data')
                pickledData={'q_table':self.q_table, 'e':self.epsilon, 'allRewards':self.allRewards}
                pickle.dump(pickledData, open(self.checkPointName, "wb"))

        print('training finished')

    ## Return system operator set reference for series compensation device. Assumed that the mean of all lines is the goal
    def lp_ref(self):
        return stat.mean(self.env_2bus.net.res_line.loading_percent)

    ## Run environment with FACTS but no RL, series compensation TRUE or FALSE
    def runFACTSnoRL(self, v_ref, lp_ref, bus_index_shunt, bus_index_voltage, line_index, series_comp_enabl):
        # Enable/Disable devices
        self.env_2bus.net.switch.at[1, 'closed'] = False if series_comp_enabl else True
        self.env_2bus.net.switch.at[0, 'closed'] = True
        self.env_2bus.net.controller.in_service[1] = True if series_comp_enabl else False

        # Set reference values
        self.env_2bus.shuntControl.ref = v_ref;
        self.env_2bus.seriesControl.ref = lp_ref;
        self.env_2bus.runEnv(runControl=True)
        busVoltage = self.env_2bus.net.res_bus.vm_pu[bus_index_voltage]
        lp_max = max(self.env_2bus.net.res_line.loading_percent)
        lp_std = np.std(self.env_2bus.net.res_line.loading_percent)
        return busVoltage, lp_max, lp_std

    ## Run the environment controlled by greedy RL
    def runFACTSgreedyRL(self, busVoltageIndex, currentState,takeLastAction):
        #print(currentState)
        actionIndex = self.q_table[currentState].idxmax()
        #if len(self.q_table[currentState].unique()) == 1:
        #    print(currentState)
        action = self.getActionFromIndex(actionIndex)
        nextStateMeasurements, reward, done, measAfterAction = self.env_2bus.takeAction(action[0], action[1])
        busVoltage = measAfterAction[0]
        lp_max = measAfterAction[1]
        lp_std = measAfterAction[2]
        return nextStateMeasurements, busVoltage, lp_max, lp_std, reward

    # Compare performance wrt reward and voltage stability between RL agent, benchmark and non-RL cases.
    # Creates selection of graphs and prints other results.
    def comparePerformance(self, steps, oper_upd_interval, bus_index_shunt, bus_index_voltage, line_index,
                           benchmarkFlag):
        v_noFACTS = []
        lp_max_noFACTS = []
        lp_std_noFACTS = []
        v_FACTS = []
        lp_max_FACTS = []
        lp_std_FACTS = []
        v_RLFACTS = []
        lp_max_RLFACTS = []
        lp_std_RLFACTS = []
        v_FACTS_noSeries = []
        lp_max_FACTS_noSeries = []
        lp_std_FACTS_noSeries = []
        v_FACTS_eachTS = []
        lp_max_FACTS_eachTS = []
        lp_std_FACTS_eachTS = []
        rewardNoFacts = []
        rewardFacts = []
        rewardFactsEachTS = []
        rewardFactsNoSeries = []
        rewardFactsRL = []
        v_RLFACTS_AfterLoadChange = []
        lp_max_RLFACTS_AfterLoadChange = []
        self.env_2bus.setMode('test')
        self.env_2bus.reset()
        self.env_2bus.stateIndex += 3 #+3 to get in phase with DQN and TD3 and benchmark
        stateIndex = self.env_2bus.stateIndex
        loadProfile = self.env_2bus.loadProfile
        performance = 0
        while stateIndex + steps + 4 > len(loadProfile):
            self.env_2bus.reset()  # Reset to get sufficient number of steps left in time series
            stateIndex = self.env_2bus.stateIndex+3
            loadProfile = self.env_2bus.loadProfile

        # Create copy of network for historic measurements
        temp = copy.deepcopy(self)
        currentMeasurements = temp.env_2bus.getCurrentState();
        # temp.eval_net.eval()

        # Need seperate copy for each scenario
        stateIndex = temp.env_2bus.stateIndex
        qObj_env_noFACTS = copy.deepcopy(temp)
        qObj_env_FACTS = copy.deepcopy(temp)
        qObj_env_RLFACTS = copy.deepcopy(temp)
        qObj_env_FACTS_noSeries = copy.deepcopy(temp)
        qObj_env_FACTS_eachTS = copy.deepcopy(temp)

        # Make sure FACTS devices disabled for noFACTS case and no Series for that case
        qObj_env_noFACTS.env_2bus.net.switch.at[0, 'closed'] = False
        qObj_env_noFACTS.env_2bus.net.switch.at[1, 'closed'] = True
        qObj_env_FACTS_noSeries.env_2bus.net.switch.at[1, 'closed'] = True

        # To plot horizontal axis in nose-curve
        load_nom_pu = 2  # the nominal IEEE load in pu
        print(stateIndex)
        print(qObj_env_RLFACTS.env_2bus.stateIndex)
        loading_arr = list(load_nom_pu * (loadProfile[stateIndex:stateIndex + steps] / stat.mean(loadProfile)))
        loading_arr_afterLoadChange = list(load_nom_pu * (loadProfile[stateIndex+1:stateIndex + steps+1] / stat.mean(loadProfile))) # to get proper sorting for voltage after load change


        # Loop through each load
        for i in range(0, steps):
            # no FACTS
            qObj_env_noFACTS.env_2bus.runEnv(runControl=False)  # No FACTS, no control
            v_noFACTS.append(qObj_env_noFACTS.env_2bus.net.res_bus.vm_pu[bus_index_voltage])
            lp_max_noFACTS.append(max(qObj_env_noFACTS.env_2bus.net.res_line.loading_percent))
            lp_std_noFACTS.append(np.std(qObj_env_noFACTS.env_2bus.net.res_line.loading_percent))
            rewardNoFacts.append((200 + (math.exp(abs(1 - qObj_env_noFACTS.env_2bus.net.res_bus.vm_pu[bus_index_voltage]) * 10) * -20) - np.std(qObj_env_noFACTS.env_2bus.net.res_line.loading_percent)) / 200)

            # FACTS with both series and shunt
            v_ref = 1
            if i % oper_upd_interval == 0:
                lp_reference = qObj_env_FACTS.lp_ref()
                # print('oper', lp_reference)
            voltage, lp_max, lp_std = qObj_env_FACTS.runFACTSnoRL(v_ref, lp_reference, bus_index_shunt,
                                                                  bus_index_voltage,
                                                                  line_index, True)  # Series compensation enabled
            v_FACTS.append(voltage)
            lp_max_FACTS.append(lp_max)
            lp_std_FACTS.append(lp_std)
            rewFacts = (200 + (math.exp(abs(1 - voltage) * 10) * -20) - lp_std) / 200;

            # FACTS no Series compensation
            voltage, lp_max, lp_std = qObj_env_FACTS_noSeries.runFACTSnoRL(v_ref, lp_reference, bus_index_shunt,
                                                                           bus_index_voltage,
                                                                           line_index,
                                                                           False)  # Series compensation disabled
            v_FACTS_noSeries.append(voltage)
            lp_max_FACTS_noSeries.append(lp_max)
            lp_std_FACTS_noSeries.append(lp_std)
            rewFactsNoSeries = (200 + (math.exp(abs(1 - voltage) * 10) * -20) - lp_std) / 200;

            # FACTS with both series and shunt, with system operator update EACH time step
            lp_reference_eachTS = qObj_env_FACTS_eachTS.lp_ref()
            # print('eachTS', lp_reference_eachTS)
            voltage, lp_max, lp_std = qObj_env_FACTS_eachTS.runFACTSnoRL(v_ref, lp_reference_eachTS, bus_index_shunt,
                                                                         bus_index_voltage,
                                                                         line_index,
                                                                         True)  # Series compensation enabled
            v_FACTS_eachTS.append(voltage)
            lp_max_FACTS_eachTS.append(lp_max)
            lp_std_FACTS_eachTS.append(lp_std)
            # rewFactsEachTS=(200+(math.exp(abs(1 - voltage) * 10) * -20) - lp_std)/200 ;

            # RLFACTS
            takeLastAction = False;
            oldMeasurements = currentMeasurements
            currentState = temp.getStateFromMeasurements_2([oldMeasurements, currentMeasurements]);
            currentMeasurements, voltage, lp_max, lp_std, r = qObj_env_RLFACTS.runFACTSgreedyRL(bus_index_voltage,
                                                                                                currentState,
                                                                                                takeLastAction)  # runpp is done within this function

            v_RLFACTS.append(voltage)
            lp_max_RLFACTS.append(lp_max)
            lp_std_RLFACTS.append(lp_std)
            rewardFactsRL.append(r)  # FACTS with both series and shunt
            currentMeasurements = qObj_env_RLFACTS.env_2bus.getCurrentState();
            v_RLFACTS_AfterLoadChange.append(qObj_env_RLFACTS.env_2bus.net.res_bus.vm_pu[1])
            lp_max_RLFACTS_AfterLoadChange.append(max(qObj_env_RLFACTS.env_2bus.net.res_line.loading_percent))

            # Increment state
            stateIndex += 1
            qObj_env_noFACTS.env_2bus.scaleLoadAndPowerValue(stateIndex)  # Only for these, rest are incremented within their respective functions
            qObj_env_FACTS.env_2bus.scaleLoadAndPowerValue(stateIndex)
            qObj_env_FACTS_noSeries.env_2bus.scaleLoadAndPowerValue(stateIndex)
            qObj_env_FACTS_eachTS.env_2bus.scaleLoadAndPowerValue(stateIndex)
            rewFacts = 0.7 * rewFacts + 0.3 * (
                    200 + (math.exp(abs(1 - qObj_env_FACTS.env_2bus.net.res_bus.vm_pu[1]) * 10) * -20) - np.std(
                qObj_env_FACTS.env_2bus.net.res_line.loading_percent)) / 200
            rewardFacts.append(rewFacts)
            rewFactsNoSeries = 0.7 * rewFactsNoSeries + 0.3 * (200 + (
                    math.exp(abs(1 - qObj_env_FACTS_noSeries.env_2bus.net.res_bus.vm_pu[1]) * 10) * -20) - np.std(
                qObj_env_FACTS_noSeries.env_2bus.net.res_line.loading_percent)) / 200
            rewardFactsNoSeries.append(rewFactsNoSeries)
            rewFactsEachTS = 0.7 * rewFacts + 0.3 * (200 + (
                    math.exp(abs(1 - qObj_env_FACTS_eachTS.env_2bus.net.res_bus.vm_pu[1]) * 10) * -20) - np.std(
                qObj_env_FACTS_eachTS.env_2bus.net.res_line.loading_percent)) / 200
            rewardFactsEachTS.append(rewFactsEachTS)  # FACTS with both series and shunt
            if (rewFacts - r < 0.01) and (rewFactsNoSeries - r < 0.01):
                performance += 1;

        print('RL better than no RL in % wrt to reward (Upsilon): ', (performance / steps)*100)
        print('max reward facts:', np.max(rewardFacts))
        print('max reward facts with RL:', np.max(rewardFactsRL))
        print('max reward facts no series:', np.max(rewardFactsNoSeries))
        print('min reward facts:', np.min(rewardFacts))
        print('min reward facts with RL:', np.min(rewardFactsRL))
        print('min reward facts no series:', np.min(rewardFactsNoSeries))
        print('mean reward facts:', np.mean(rewardFacts))
        print('mean reward facts with RL:', np.mean(rewardFactsRL))
        print('mean reward facts no series:', np.mean(rewardFactsNoSeries))
        print('std reward facts:', np.std(rewardFacts))
        print('std reward facts with RL:', np.std(rewardFactsRL))
        print('std reward facts no series:', np.std(rewardFactsNoSeries))

        #remove last element in voltage after load change to get correct dimensions
        v_RLFACTS_AfterLoadChange.pop()

        # Get benchmark from pickle files:
        with open('Data/voltBenchmark.pkl', 'rb') as pickle_file:
            v_RLFACTS_Benchmark = pickle.load(pickle_file)
            v_RLFACTS_Benchmark = v_RLFACTS_Benchmark[0:steps]
        with open('Data/lpmaxBenchmark.pkl', 'rb') as pickle_file:
            lp_max_RLFACTS_Benchmark = pickle.load(pickle_file)
            lp_max_RLFACTS_Benchmark = lp_max_RLFACTS_Benchmark[0:steps]
        with open('Data/lpstdBenchmark.pkl', 'rb') as pickle_file:
            lp_std_RLFACTS_Benchmark = pickle.load(pickle_file)
            #print(lp_std_RLFACTS_Benchmark)
            lp_std_RLFACTS_Benchmark = lp_std_RLFACTS_Benchmark[0:steps]
            #print(lp_std_RLFACTS_Benchmark)
        with open('Data/rewBenchmark.pkl', 'rb') as pickle_file:
            rewardFactsBenchmark = pickle.load(pickle_file)
            rewardFactsBenchmark = rewardFactsBenchmark[0:steps]

        # Make plots
        i_list = list(range(863, 863 + steps))
        lw = 1.8
        fig, ax1 = plt.subplots()
        color = 'tab:blue'
        ax1.set_title('Voltage and line loading standard deviation for test set', fontsize=23)
        ax1.set_xlabel('Time step [-]', fontsize=19)
        ax1.set_ylabel('Bus Voltage [pu]', color=color, fontsize=19)
        ax1.plot(i_list, v_noFACTS, color=color)
        ax1.plot(i_list, v_FACTS, color='g')
        ax1.plot(i_list, v_FACTS_noSeries, color='k')
        ax1.plot(i_list, v_RLFACTS, color='r')
        # ax1.plot(i_list, v_FACTS_eachTS, color= 'c')
        if benchmarkFlag:
            ax1.plot(i_list, v_RLFACTS_Benchmark, color='y')

        # ax1.legend(['v no facts', 'v facts' , 'v facts no series comp','v RL facts', 'v RL facts upd each ts', 'v RL benchmark'], loc=2)
        ax1.legend(['v no FACTS', 'v shunt+series', 'v hunt only', 'v $Q$-learning', 'v RL benchmark'], loc=2, fontsize=14)
        ax2 = ax1.twinx()

        color = 'tab:blue'
        ax2.set_ylabel('line loading percentage std [% units]', color='m', fontsize=19)
        ax2.plot(i_list, lp_std_noFACTS, color=color, linestyle='dashed')
        ax2.plot(i_list, lp_std_FACTS, color='g', linestyle='dashed')
        ax2.plot(i_list, lp_std_FACTS_noSeries, color='k', linestyle='dashed')
        ax2.plot(i_list, lp_std_RLFACTS, color='r', linestyle='dashed')
        # ax2.plot(i_list, lp_std_FACTS_eachTS, color='c', linestyle = 'dashed')
        if benchmarkFlag:
            ax2.plot(i_list, lp_std_RLFACTS_Benchmark, color='y', linestyle='dashed')
        # ax2.legend(['std lp no facts', 'std lp facts', 'std lp facts no series comp', 'std lp RL facts', 'std lp facts each ts', 'std lp RL benchmark' ], loc=1)
        ax2.legend(['std lp no FACTS', 'std lp shunt+series', 'std lp shunt only', 'std lp $Q$-learning',
                    'std lp RL benchmark'], loc=1, fontsize=14)
        plt.grid()
        plt.show()

        # Plot Rewards
        fig2, (ax1,ax2,ax3) = plt.subplots(3, 1, sharex=True, sharey=True)
        fig2.suptitle('Rewards along the test set', fontsize=24)
        plt.xlabel('Time step [-]', Figure=fig2, fontsize=20)
        ax1.set_ylabel('Reward [-]', Figure=fig2, fontsize=20)
        ax2.set_ylabel('Reward [-]', Figure=fig2, fontsize=20)
        ax3.set_ylabel('Reward [-]', Figure=fig2, fontsize=20)
        plt.xticks(fontsize=16)
        plt.yticks(fontsize=16)
        xtickers = [800,900,1000,1100,1200,1300,1400]
        ytickers = [0.5, 0.6, 0.7, 0.8,0.9]
        ax1.set_xticklabels(xtickers,fontsize=16)
        ax1.set_yticklabels(ytickers,fontsize=16)
        ax2.set_xticklabels(xtickers,fontsize=16)
        ax2.set_yticklabels(ytickers,fontsize=16)
        ax3.set_xticklabels(xtickers,fontsize=16)
        ax3.set_yticklabels(ytickers,fontsize=16)
        ax1.plot(i_list, rewardFactsRL, Figure=fig2, color='tab:red')
        if benchmarkFlag:
            ax1.plot(i_list, rewardFactsBenchmark, Figure=fig2, color='tab:olive')
        ax2.plot(i_list, rewardFacts, Figure=fig2, color='tab:green')
        ax2.plot(i_list, rewardFactsNoSeries, Figure=fig2, color='k')
        ax3.plot(i_list, rewardNoFacts, Figure=fig2, color='tab:brown')
        #plt.title('Rewards along the test set', fontsize=24)
        ax1.legend(['$Q$-learning', 'RL benchmark'],
                   loc=3, fontsize=14)
        ax2.legend(['shunt+series', 'shunt only'],
                   loc=3, fontsize=14)
        ax3.legend(['no FACTS'],
                   loc=3, fontsize=14)
        ax1.grid()
        ax1.minorticks_on()
        ax1.grid(b=True, which='minor', color='#999999', linestyle='-', alpha=0.2)
        ax2.grid()
        ax2.minorticks_on()
        ax2.grid(b=True, which='minor', color='#999999', linestyle='-', alpha=0.2)
        ax3.grid()
        ax3.minorticks_on()
        ax3.grid(b=True, which='minor', color='#999999', linestyle='-', alpha=0.2)
        plt.show()

        ## Calculate measure for comparing RL and Benchmark wrt reward.
        performanceFactsRL = 0
        performanceFacts = 0
        performanceFactsnoSeries = 0
        PerformanceNoFacts = 0
        for i in range(0, steps):
            performanceFactsRL += math.sqrt((rewardFactsRL[i] - rewardFactsBenchmark[i]) ** 2)
            performanceFacts += math.sqrt((rewardFacts[i] - rewardFactsBenchmark[i]) ** 2)
            performanceFactsnoSeries += math.sqrt((rewardFactsNoSeries[i] - rewardFactsBenchmark[i]) ** 2)
            PerformanceNoFacts += math.sqrt((rewardNoFacts[i] - rewardFactsBenchmark[i]) ** 2)

        print('')
        print('performance FACTS RL (Psi_rootsquare): ', performanceFactsRL)
        print('performance FACTS shunt+series (Psi_rootsquare): ', performanceFacts)
        print('performance FACTS shunt only (Psi_rootsquare): ', performanceFactsnoSeries)
        print('performance no FACTS (Psi_rootsquare): ', PerformanceNoFacts)

        # Nosecurve:
        loading_arr_sorted = sorted(loading_arr)
        loading_arr_afterLoadChange_sorted = sorted(loading_arr_afterLoadChange)

        # Sort the measurements
        v_noFACTS_sorted = [x for _, x in sorted(zip(loading_arr, v_noFACTS))]
        lp_max_noFACTS_sorted = [x for _, x in sorted(zip(loading_arr, lp_max_noFACTS))]
        v_FACTS_sorted = [x for _, x in sorted(zip(loading_arr, v_FACTS))]
        lp_max_FACTS_sorted = [x for _, x in sorted(zip(loading_arr, lp_max_FACTS))]
        v_RLFACTS_sorted = [x for _, x in sorted(zip(loading_arr, v_RLFACTS))]
        lp_max_RLFACTS_sorted = [x for _, x in sorted(zip(loading_arr, lp_max_RLFACTS))]
        v_FACTS_noSeries_sorted = [x for _, x in sorted(zip(loading_arr, v_FACTS_noSeries))]
        lp_max_FACTS_noSeries_sorted = [x for _, x in sorted(zip(loading_arr, lp_max_FACTS_noSeries))]
        v_FACTS_eachTS_sorted = [x for _, x in sorted(zip(loading_arr, v_FACTS_eachTS))]
        lp_max_FACTS_eachTS_sorted = [x for _, x in sorted(zip(loading_arr, lp_max_FACTS_eachTS))]
        if benchmarkFlag:
            v_RLFACTS_Benchmark_sorted = [x for _, x in sorted(zip(loading_arr, v_RLFACTS_Benchmark))]
            lp_max_RLFACTS_Benchmark_sorted = [x for _, x in sorted(zip(loading_arr, lp_max_RLFACTS_Benchmark))]
        v_RLFACTS_AfterLoadChange_sorted = [x for _, x in sorted(zip(loading_arr_afterLoadChange, v_RLFACTS_AfterLoadChange))]
        lp_max_RLFACTS_AfterLoadChange_sorted = [x for _, x in
                                                 sorted(zip(loading_arr_afterLoadChange, lp_max_RLFACTS_AfterLoadChange))]
        print('')
        print('maximum loading percentage noFACTS  ', max(lp_max_noFACTS))
        print('maximum loading percentage Shunt+Series  ', max(lp_max_FACTS))
        print('maximum loading percentage shunt only  ', max(lp_max_FACTS_noSeries))
        print('maximum loading percentage after action RL: ', max(lp_max_RLFACTS_Benchmark))
        print('maximum loading percentage after load change RL: ', max(lp_max_RLFACTS_AfterLoadChange))

        # Trim arrays to only include values <= X % loading percentage
        lp_limit_for_noseCurve = 100
        lp_max_noFACTS_sorted_trim = [x for x in lp_max_noFACTS_sorted if x <= lp_limit_for_noseCurve]
        lp_max_FACTS_sorted_trim = [x for x in lp_max_FACTS_sorted if x <= lp_limit_for_noseCurve]
        lp_max_RLFACTS_sorted_trim = [x for x in lp_max_RLFACTS_sorted if x <= lp_limit_for_noseCurve]
        lp_max_FACTS_noSeries_sorted_trim = [x for x in lp_max_FACTS_noSeries_sorted if x <= lp_limit_for_noseCurve]
        lp_max_FACTS_eachTS_sorted_trim = [x for x in lp_max_FACTS_eachTS_sorted if x <= lp_limit_for_noseCurve]
        if benchmarkFlag:
            lp_max_RLFACTS_Benchmark_sorted_trim = [x for x in lp_max_RLFACTS_Benchmark_sorted if
                                                    x <= lp_limit_for_noseCurve]
        lp_max_RLFACTS_AfterLoadChange_sorted_trim = [x for x in lp_max_RLFACTS_AfterLoadChange_sorted if
                                                      x <= lp_limit_for_noseCurve]

        v_noFACTS_sorted_trim = v_noFACTS_sorted[0:len(lp_max_noFACTS_sorted_trim)]
        v_FACTS_sorted_trim = v_FACTS_sorted[0:len(lp_max_FACTS_sorted_trim)]
        v_RLFACTS_sorted_trim = v_RLFACTS_sorted[0:len(lp_max_RLFACTS_sorted_trim)]
        v_FACTS_noSeries_sorted_trim = v_FACTS_noSeries_sorted[0:len(lp_max_FACTS_noSeries_sorted_trim)]
        v_FACTS_eachTS_sorted_trim = v_FACTS_eachTS_sorted[0:len(lp_max_FACTS_eachTS_sorted_trim)]
        if benchmarkFlag:
            v_RLFACTS_Benchmark_sorted_trim = v_RLFACTS_Benchmark_sorted[0:len(lp_max_RLFACTS_Benchmark_sorted_trim)]
        v_RLFACTS_AfterLoadChange_sorted_trim = v_RLFACTS_AfterLoadChange_sorted[
                                                0:len(lp_max_RLFACTS_AfterLoadChange_sorted_trim)]

        loading_arr_plot_noFACTS = loading_arr_sorted[0:len(lp_max_noFACTS_sorted_trim)]
        loading_arr_plot_FACTS = loading_arr_sorted[0:len(lp_max_FACTS_sorted_trim)]
        loading_arr_plot_RLFACTS = loading_arr_sorted[0:len(lp_max_RLFACTS_sorted_trim)]
        loading_arr_plot_FACTS_noSeries = loading_arr_sorted[0:len(lp_max_FACTS_noSeries_sorted_trim)]
        loading_arr_plot_FACTS_eachTS = loading_arr_sorted[0:len(lp_max_FACTS_eachTS_sorted_trim)]
        if benchmarkFlag:
            loading_arr_plot_RLFACTS_Benchmark = loading_arr_sorted[0:len(lp_max_RLFACTS_Benchmark_sorted_trim)]
        loading_arr_plot_RLFACTS_AfterLoadChange = loading_arr_afterLoadChange_sorted[
                                                   0:len(lp_max_RLFACTS_AfterLoadChange_sorted_trim) + 0]

        # Print result wrt trimmed voltage
        print('')
        print('max voltage facts (v1):', np.max(v_FACTS_sorted_trim))
        print('max voltage facts with RL (v1):', np.max(v_RLFACTS_sorted_trim))
        print('max voltage facts no series (v1):', np.max(v_FACTS_noSeries_sorted_trim))
        print('min voltage facts (v1):', np.min(v_FACTS_sorted_trim))
        print('min voltage facts with RL (v1):', np.min(v_RLFACTS_sorted_trim))
        print('min voltage facts no series (v1):', np.min(v_FACTS_noSeries_sorted_trim))
        print('mean voltage facts (v1):', np.mean(v_FACTS_sorted_trim))
        print('mean voltage facts with RL (v1):', np.mean(v_RLFACTS_sorted_trim))
        print('mean voltage facts no series (v1):', np.mean(v_FACTS_noSeries_sorted_trim))
        print('std voltage facts (v1):', np.std(v_FACTS_sorted_trim))
        print('std voltage facts with RL (v1):', np.std(v_RLFACTS_sorted_trim))
        print('std voltage facts no series (v1):', np.std(v_FACTS_noSeries_sorted_trim))
        print('')
        print('max voltage RL after load change (v2): ', np.max(v_RLFACTS_AfterLoadChange))
        print('min voltage RL after load change (v2): ', np.min(v_RLFACTS_AfterLoadChange))
        print('mean voltage RL after load change (v2): ', np.mean(v_RLFACTS_AfterLoadChange))
        print('std voltage RL after load change (v2): ', np.std(v_RLFACTS_AfterLoadChange))

        # Plot Nose Curve
        fig3 = plt.figure()
        markersize =44
        plt.scatter(loading_arr_plot_noFACTS, v_noFACTS_sorted_trim, marker='x', Figure=fig3, color='tab:brown', s=markersize)
        plt.scatter(loading_arr_plot_FACTS, v_FACTS_sorted_trim, marker='v', Figure=fig3, color='tab:green', s=markersize)
        plt.scatter(loading_arr_plot_FACTS_noSeries, v_FACTS_noSeries_sorted_trim, marker='^', Figure=fig3, color='k',
                    s=markersize)
        plt.scatter(loading_arr_plot_RLFACTS, v_RLFACTS_sorted_trim, marker='D', Figure=fig3, color='tab:red', s=markersize*1.6)
        plt.scatter(loading_arr_plot_RLFACTS_AfterLoadChange, v_RLFACTS_AfterLoadChange_sorted_trim, marker='d', Figure=fig3,
                    color='tab:blue', s=markersize)
        if benchmarkFlag:
            plt.plot(loading_arr_plot_RLFACTS_Benchmark, v_RLFACTS_Benchmark_sorted_trim, Figure=fig3, color='tab:olive', linewidth=lw*1.5)#, s=markersize, marker='*')
        plt.title('Nose-curve from test set with sorted voltage levels', fontsize=24)
        plt.xlabel('Loading [pu]', Figure=fig3, fontsize=20)
        plt.ylabel('Bus Voltage [pu]', Figure=fig3, fontsize=20)
        plt.xticks(fontsize=16)
        plt.yticks(fontsize=16)
        # plt.legend(['v no FACTS', 'v FACTS', 'v FACTS no series comp','v RL FACTS', 'v FACTS each ts', 'v RL FACTS benchmark.'], loc=1)
        plt.legend(['RL benchmark','no FACTS', 'shunt+series', 'shunt only', '$Q$-learning $v_1$', '$Q$-learning $v_2$'], loc=3, fontsize=16)
        plt.grid()
        plt.show()


