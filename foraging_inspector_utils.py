import pandas as pd
import matplotlib.pyplot as plt
import datajoint as dj
from pipeline import pipeline_tools, lab, experiment, behavior_foraging
import numpy as np
#dj.conn()


def merge_dataframes_with_nans(df_1,df_2,basiscol):
    basiscol = 'trial'
    colstoadd = list()
# =============================================================================
#     df_1 = df_behaviortrial
#     df_2 = df_reactiontimes
# =============================================================================
    for colnow in df_2.keys():
        if colnow not in df_1.keys():
            df_1[colnow] = np.nan
            colstoadd.append(colnow)
    for line in df_2.iterrows():
        for colname in colstoadd:
            df_1.loc[df_1[basiscol]==line[1][basiscol],colname]=line[1][colname]
    return df_1

def multicolor_ylabel(ax,list_of_strings,list_of_colors,axis='x',anchorpad=0,**kw):
    """this function creates axes labels with multiple colors
    ax specifies the axes object where the labels should be drawn
    list_of_strings is a list of all of the text items
    list_if_colors is a corresponding list of colors for the strings
    axis='x', 'y', or 'both' and specifies which label(s) should be drawn"""
    from matplotlib.offsetbox import AnchoredOffsetbox, TextArea, HPacker, VPacker

    # x-axis label
    if axis=='x' or axis=='both':
        boxes = [TextArea(text, textprops=dict(color=color, ha='left',va='bottom',**kw)) 
                    for text,color in zip(list_of_strings,list_of_colors) ]
        xbox = HPacker(children=boxes,align="center",pad=0, sep=5)
        anchored_xbox = AnchoredOffsetbox(loc=3, child=xbox, pad=anchorpad,frameon=False,bbox_to_anchor=(0.2, -0.09),
                                          bbox_transform=ax.transAxes, borderpad=0.)
        ax.add_artist(anchored_xbox)

    # y-axis label
    if axis=='y' or axis=='both':
        boxes = [TextArea(text, textprops=dict(color=color, ha='left',va='bottom',rotation=90,**kw)) 
                     for text,color in zip(list_of_strings[::-1],list_of_colors) ]
        ybox = VPacker(children=boxes,align="center", pad=0, sep=5)
        anchored_ybox = AnchoredOffsetbox(loc=3, child=ybox, pad=anchorpad, frameon=False, bbox_to_anchor=(-0.10, 0.2), 
                                          bbox_transform=ax.transAxes, borderpad=0.)
        ax.add_artist(anchored_ybox)
        

def plot_trials(ax1,
                ax2=None,
                plottype = '2lickport',
                wr_name = 'FOR01',
                sessions = (5,11),
                plot_every_choice = True,
                show_bias_check_trials = True,
                choice_filter = np.ones(10)/10): 
    """This function downloads foraging sessions from datajoint and plots them"""
    
    #%%
# =============================================================================
#     fig=plt.figure()
#     ax1=fig.add_axes([0,0,2,.8])
#     ax2=fig.add_axes([0,-1,2,.8])
#     plottype = '2lickport'
#     wr_name = 'FOR11'
#     sessions = (1,46)
#     plot_every_choice = True
#     show_bias_check_trials = True
#     choice_filter = np.ones(10)/10
# =============================================================================

    
    ax1.clear()
    subject_id = (lab.WaterRestriction()&'water_restriction_number = "{}"'.format(wr_name)).fetch1('subject_id')
    
    df_behaviortrial = pd.DataFrame(np.asarray((experiment.BehaviorTrial()* experiment.SessionTrial() * experiment.SessionBlock()* behavior_foraging.TrialReactionTime &
                                    'subject_id = {}'.format(subject_id) &
                                    'session >= {}'.format(sessions[0]) &
                                    'session <= {}'.format(sessions[1])).fetch('session',
                                                                               'trial',
                                                                               'p_reward_right',
                                                                               'p_reward_left',
                                                                               'p_reward_middle',
                                                                               'trial_choice',
                                                                               'outcome'
                                                                              )).T,columns = ['session',
                                                                                              'trial',
                                                                                              'p_reward_right',
                                                                                              'p_reward_left',
                                                                                              'p_reward_middle',
                                                                                              'trial_choice',
                                                                                              'outcome'])
    
    

    unique_sessions = df_behaviortrial['session'].unique()
    for session in unique_sessions:
        total_trials_so_far = (behavior_foraging.SessionStats()&'subject_id = {}'.format(subject_id) &'session < {}'.format(session)).fetch('session_total_trial_num')
        bias_check_trials_now = (behavior_foraging.SessionStats()&'subject_id = {}'.format(subject_id) &'session = {}'.format(session)).fetch1('session_bias_check_trial_num')
        total_trials_so_far =sum(total_trials_so_far)

        df_behaviortrial.loc[df_behaviortrial['session']==session, 'trial'] += total_trials_so_far
    
    if not show_bias_check_trials:
        realtraining = (df_behaviortrial['p_reward_left']<1) & (df_behaviortrial['p_reward_right']<1) & ((df_behaviortrial['p_reward_middle']<1) | df_behaviortrial['p_reward_middle'].isnull())
        df_behaviortrial = df_behaviortrial[realtraining]
        df_behaviortrial = df_behaviortrial.reset_index(drop=True)
    
    
    df_behaviortrial['trial_choice_plot'] = np.nan
    df_behaviortrial.loc[df_behaviortrial['trial_choice'] == 'left', 'trial_choice_plot'] = 0
    df_behaviortrial.loc[df_behaviortrial['trial_choice'] == 'right', 'trial_choice_plot'] = 1
    df_behaviortrial.loc[df_behaviortrial['trial_choice'] == 'middle', 'trial_choice_plot'] = .5

    trial_choice_plot_interpolated = df_behaviortrial['trial_choice_plot'].values
    nans, x= np.isnan(trial_choice_plot_interpolated), lambda z: z.nonzero()[0]
    trial_choice_plot_interpolated[nans]= np.interp(x(nans), x(~nans), trial_choice_plot_interpolated[~nans])

    if plottype == '2lickport':
        
        #df_behaviortrial['reward_ratio']=df_behaviortrial['p_reward_right']/(df_behaviortrial['p_reward_right']+df_behaviortrial['p_reward_left'])
        df_behaviortrial['reward_ratio']=np.asarray(df_behaviortrial['p_reward_right'],float)/np.asarray(df_behaviortrial['p_reward_right']+df_behaviortrial['p_reward_left'],float)
        
        bias = np.convolve(trial_choice_plot_interpolated,choice_filter,mode = 'valid')
        bias = np.concatenate((np.nan*np.ones(int(np.floor((len(choice_filter)-1)/2))),bias,np.nan*np.ones(int(np.ceil((len(choice_filter)-1)/2)))))
    elif plottype == '3lickport':
        df_behaviortrial['reward_ratio_1']=df_behaviortrial['p_reward_left']/(df_behaviortrial['p_reward_right']+df_behaviortrial['p_reward_left']+ df_behaviortrial['p_reward_middle'])
        df_behaviortrial['reward_ratio_2']=(df_behaviortrial['p_reward_left']+df_behaviortrial['p_reward_middle'])/(df_behaviortrial['p_reward_right']+df_behaviortrial['p_reward_left']+ df_behaviortrial['p_reward_middle'])
        #%
        leftchoices_filtered = np.convolve(df_behaviortrial['trial_choice'] == 'left',choice_filter,mode = 'valid')
        leftchoices_filtered = np.concatenate((np.nan*np.ones(int(np.floor((len(choice_filter)-1)/2))),leftchoices_filtered ,np.nan*np.ones(int(np.ceil((len(choice_filter)-1)/2)))))
        rightchoices_filtered = np.convolve(df_behaviortrial['trial_choice'] == 'right',choice_filter,mode = 'valid')
        rightchoices_filtered = np.concatenate((np.nan*np.ones(int(np.floor((len(choice_filter)-1)/2))),rightchoices_filtered ,np.nan*np.ones(int(np.ceil((len(choice_filter)-1)/2)))))
        middlechoices_filtered = np.convolve(df_behaviortrial['trial_choice'] == 'middle',choice_filter,mode = 'valid')
        middlechoices_filtered = np.concatenate((np.nan*np.ones(int(np.floor((len(choice_filter)-1)/2))),middlechoices_filtered ,np.nan*np.ones(int(np.ceil((len(choice_filter)-1)/2)))))
        allchoices_filtered = np.convolve(df_behaviortrial['trial_choice'] != 'none',choice_filter,mode = 'valid')
        allchoices_filtered = np.concatenate((np.nan*np.ones(int(np.floor((len(choice_filter)-1)/2))),allchoices_filtered ,np.nan*np.ones(int(np.ceil((len(choice_filter)-1)/2)))))

    rewarded = (df_behaviortrial['outcome']=='hit')
    unrewarded = (df_behaviortrial['outcome']=='miss')
    
    blockswitches = np.where(np.diff(df_behaviortrial['session'].values)>0)[0]
    if len(blockswitches)>0:
        for trialnum_now in blockswitches:
            ax1.plot([df_behaviortrial['trial'][trialnum_now],df_behaviortrial['trial'][trialnum_now]],[-.15,1.15],'b--')
            
    if plottype == '2lickport':
        if plot_every_choice:
            ax1.plot(df_behaviortrial['trial'][rewarded],df_behaviortrial['trial_choice_plot'][rewarded],'k|',color='black',markersize=30,markeredgewidth=2)
            ax1.plot(df_behaviortrial['trial'][unrewarded],df_behaviortrial['trial_choice_plot'][unrewarded],'|',color='gray',markersize=15,markeredgewidth=2)
        ax1.plot(df_behaviortrial['trial'],bias,'k-',label = 'choice')
        ax1.plot(df_behaviortrial['trial'],df_behaviortrial['reward_ratio'],'y-')
        ax1.set_yticks((0,1))
        ax1.set_yticklabels(('left','right'))
    elif plottype == '3lickport':
        ax1.stackplot(np.asarray(df_behaviortrial['trial'],float),  leftchoices_filtered/allchoices_filtered ,  middlechoices_filtered/allchoices_filtered ,  rightchoices_filtered/allchoices_filtered ,colors=['r','g','b'], alpha=0.3 )
        if plot_every_choice:
            ax1.plot(df_behaviortrial['trial'][rewarded],df_behaviortrial['trial_choice_plot'][rewarded],'k|',color='black',markersize=30,markeredgewidth=2)
            ax1.plot(df_behaviortrial['trial'][unrewarded],df_behaviortrial['trial_choice_plot'][unrewarded],'|',color='gray',markersize=15,markeredgewidth=2)
        ax1.plot(df_behaviortrial['trial'],df_behaviortrial['reward_ratio_1'],'y-')
        ax1.plot(df_behaviortrial['trial'],df_behaviortrial['reward_ratio_2'],'y-')
        ax1.set_yticks((0,.5,1))
        ax1.set_yticklabels(('left','middle','right'))
        ax1.set_ylim([-.1,1.1])
        
    ax1.set_xlim([np.min(df_behaviortrial['trial'])-10,np.max(df_behaviortrial['trial'])+10]) 
    
    # probabilities    
    if ax2:
        ax2.clear()
        ax2.plot(df_behaviortrial['trial'],df_behaviortrial['p_reward_left'],'r-')
        ax2.plot(df_behaviortrial['trial'],df_behaviortrial['p_reward_right'],'b-')
        if plottype == '3lickport':
            ax2.plot(df_behaviortrial['trial'],df_behaviortrial['p_reward_middle'],'g-')
        ax2.set_ylabel('Reward probability')
        ax2.set_xlabel('Trial #')
        if plottype == '3lickport':
            legenda = ['left','right','middle']
        else:
            legenda = ['left','right']
        ax2.legend(legenda,fontsize='small',loc = 'upper right')
        ax2.set_xlim([np.min(df_behaviortrial['trial'])-10,np.max(df_behaviortrial['trial'])+10])    
        #%%
    return ax1, ax2
    
    
def plot_efficiency_matching_bias(ax3,
                                  plottype = '2lickport',
                                  wr_name = 'FOR01',
                                  sessions = (5,11),
                                  plot_efficiency_type='sum_prob'):
# =============================================================================
#     #%%
#     fig=plt.figure()
#     ax3=fig.add_axes([0,0,2,.8])
#     plottype = '2lickport'
#     wr_name = 'FOR11'
#     sessions = (1,46)
#     plot_efficiency_type='sum_prob'
# =============================================================================

    
    subject_id = (lab.WaterRestriction()&'water_restriction_number = "{}"'.format(wr_name)).fetch1('subject_id')
    df_blockefficiency = pd.DataFrame(behavior_foraging.BlockEfficiency()*behavior_foraging.BlockStats() & 
                                      'subject_id = {}'.format(subject_id) &
                                      'session >= {}'.format(sessions[0]) &
                                      'session <= {}'.format(sessions[1]))

    df_blockefficiency =  df_blockefficiency.sort_values(["session", "block"], ascending = (True, True))
    unique_sessions = df_blockefficiency['session'].unique()
    df_blockefficiency['session_start_trialnum']=0
    session_start_trial_nums = list()
    session_end_trial_nums = list()
    for session in unique_sessions:
        total_trials_so_far = (behavior_foraging.SessionStats()&'subject_id = {}'.format(subject_id) &'session < {}'.format(session)).fetch('session_total_trial_num')
        #bias_check_trials_now = (behavior_foraging.SessionStats()&'subject_id = {}'.format(subject_id) &'session = {}'.format(session)).fetch1('session_bias_check_trial_num')
        total_trials_so_far =sum(total_trials_so_far)
        session_start_trial_nums.append(total_trials_so_far)

        total_trials_now = (behavior_foraging.SessionStats()&'subject_id = {}'.format(subject_id) &'session = {}'.format(session)).fetch1('session_total_trial_num')
        session_end_trial_nums.append(total_trials_so_far+total_trials_now)
        #bias_check_trials_now = (behavior_foraging.SessionStats()&'subject_id = {}'.format(subject_id) &'session = {}'.format(session)).fetch1('session_bias_check_trial_num')

        df_blockefficiency.loc[df_blockefficiency['session']==session, 'session_start_trialnum'] += total_trials_so_far
        blocks = df_blockefficiency.loc[df_blockefficiency['session']==session, 'block'].values
        trial_num_so_far = 0
        for block in blocks:
            block_idx_now = (df_blockefficiency['session']==session) & (df_blockefficiency['block']==block)
            blocktrialnum = df_blockefficiency.loc[block_idx_now, 'block_trial_num'].values[0]
            df_blockefficiency.loc[block_idx_now, 'trialnum_block_middle'] = total_trials_so_far + trial_num_so_far + blocktrialnum/2
            trial_num_so_far += blocktrialnum

    if plot_efficiency_type == 'max_prob':
        eff_text = 'block_effi_one_p_reward'
    elif plot_efficiency_type == 'sum_prob':
        eff_text = 'block_effi_sum_p_reward'
    elif plot_efficiency_type == 'max_available':
        eff_text = 'block_effi_one_a_reward'
    elif plot_efficiency_type == 'sum_available':
        eff_text = 'block_effi_sum_a_reward'
    ax3.plot(df_blockefficiency['trialnum_block_middle'],df_blockefficiency[eff_text],'ko-')        
    session_switch_trial_nums = session_start_trial_nums.copy()
    session_switch_trial_nums.append(session_end_trial_nums[-1])
    for session_switch_trial_num in session_switch_trial_nums:
        ax3.plot([session_switch_trial_num,session_switch_trial_num],[-.15,1.15],'b--')
    ax3.set_xlim([np.min(session_switch_trial_nums)-10,np.max(session_switch_trial_nums)+10]) 

    match_idx_r,bias_r,sessions = np.asarray((behavior_foraging.SessionMatchBias()*behavior_foraging.SessionStats()&
                                              'subject_id = {}'.format(subject_id) &
                                              'session >= {}'.format(sessions[0]) &
                                              'session <= {}'.format(sessions[1])).fetch('match_idx_r','bias_r','session'))
    bias_r = (np.asarray(bias_r,float))
    #bias_r = (np.asarray(bias_r,float)+np.log2(10))/(np.log2(10)*2) # converting it between 0 and 1
    
    session_middle_trial_nums = list()
    for session_now in sessions:
        sessionidx = np.where(session_now == unique_sessions)[0]
        if len(sessionidx)>0:
            session_middle_trial_nums.extend((np.asarray(session_start_trial_nums)[sessionidx] + np.asarray(session_end_trial_nums)[sessionidx])/2)
        else:
            session_middle_trial_nums.append(np.nan)
    ax3.plot(session_middle_trial_nums,match_idx_r,'ro-')
    ax3.set_ylim([-.1,1.1])
    ax33 = ax3.twinx()
    ax33.plot(session_middle_trial_nums,bias_r,'yo-')
    ax33.set_ylim(np.asarray([-1.1,1.1])*np.nanmin([np.nanmax(np.abs(bias_r)),4]))
    ax33.set_ylabel('Bias',color='y')
    ax33.spines["right"].set_color("yellow")
    #ax33.tick_params(axis='y', colors='yellow')
    multicolor_ylabel(ax3,('Efficiency', ' Matching '),('r','k'),axis='y',size=12)
    #%%
    return ax3
    