#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 27 21:40:53 2020

@author: yanlan
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 24 11:19:06 2020

@author: yanlan
"""

from random import randint
import pickle
import os
import numpy as np
import pandas as pd
import warnings; warnings.simplefilter("ignore")
import sys; sys.path.append("../Utilities/")
from newfun import readCLM # newfun_full
from newfun import fitVOD_RMSE,dt, hour2day, hour2week
from newfun import get_var_bounds,OB,CONST,CLAPP,ca
from newfun import GetTrace
from Utilities import nanOLS,nancorr
import time

tic = time.perf_counter()

# =========================== control pannel =============================

parentpath = '/scratch/users/yanlan/OSSE5/'
arrayid = int(os.environ['SLURM_ARRAY_TASK_ID']) # 0-119
warmup, nsample,thinning = (0.8,200,50)

# parentpath = '/Volumes/ELEMENTS/VOD_hydraulics/OSSE2/'
#arrayid = 58
#warmup, nsample,thinning = (0.8,2,20)


inpath = parentpath+ '../Input/'
hyperpara = (0.1,0.05,20)
datapath = parentpath + '../OSSE2/FakeData/'; 

baseid = int(arrayid/53)
fid = int(arrayid-baseid*53)

if baseid==0:
    versionpath = parentpath + 'Low/'; noise_level = 0
elif baseid==1:
    versionpath = parentpath + 'Medium/'; noise_level = 1
elif baseid==2:
    versionpath = parentpath + 'High/'; noise_level = 2
elif baseid==3:
    versionpath = parentpath + 'Test/'; noise_level = 2
    
outpath = versionpath +'Output/'
forwardpath = versionpath+'Forward/'
statspath = versionpath+'STATS/'
# obspath = versionpath+'../OBS_STATS/'; OBSstats = 0
if baseid==3:
    MODE_list = ['VOD_ET','VOD_SM_ET']
else:
    MODE_list = ['VOD_ET','VOD_ET_ISO','VOD_SM','VOD_SM_ISO','VOD_SM_ET','VOD_SM_ET_ISO']

SiteInfo = pd.read_csv('SiteInfo_reps_53.csv')


def calR2(yhat,y):
    return 1-np.nanmean((y-yhat)**2)/np.nanmean((y-np.nanmean(y))**2)

sitename = str(SiteInfo['row'].values[fid])+'_'+str(SiteInfo['col'].values[fid])
Forcings,VOD,SOILM,ET,dLAI,discard_vod,discard_et,idx = readCLM(inpath,sitename)
    
with open(datapath+'Gen_'+sitename+'_'+str(noise_level)+'.pkl', 'rb') as f: 
    VOD_fake,ET_fake,SOILM_fake = pickle.load(f)
print(datapath+'Gen_'+sitename+'_'+str(noise_level)+'.pkl')
ET = np.copy(ET_fake)
VOD_ma = np.copy(VOD_fake)
SOILM = np.copy(SOILM_fake)

Z_r,tx = (SiteInfo['Root depth'].values[fid]*1000,int(SiteInfo['Soil texture'].values[fid]))
 
psi0cm = CLAPP.psat[tx]
phi0 = -psi0cm/100*9.8*1000/10**6 #MPa # *10**6/9.8 
phi0_mm = -psi0cm*10 # mm
n = CLAPP.thetas[tx]
ksoil = CLAPP.ksat[tx]*60*10  #cm/s to mm/hr
sinit = 0.28
d1 = 50
d2 = Z_r-d1
m1 = -d1/2
m2 = -(d1+d2/2)
m3 = -(d1+d2+1000)
 
# Calculations not affected by MCMC paramteres
RNET,TEMP,P,VPD,Psurf,GA,LAI,VegK = Forcings
N = len(RNET)
 
# Terms in Farquhar's model of biochemical demand for CO2
PAR = RNET/(CONST.Ephoton*CONST.NA)*1e6
T_C = TEMP-CONST.U3 # degree C
Kc = 300*np.exp(0.074*(T_C-25)) # umol/mol
Ko = 300*np.exp(0.015*(T_C-25)) # mmol/mol
cp = 36.9+1.18*(T_C-25)+0.036*(T_C-25)**2
Vcmax25 = SiteInfo['Vcmax25'].values[fid]
Vcmax0 = Vcmax25*np.exp(50*(TEMP-298)/(298*CONST.R*TEMP))
Jmax = Vcmax0*np.exp(1)

# Vcmax0 = OB.koptv*OB.Hdv*np.exp(OB.Hav*(TEMP-OB.Toptv)/TEMP/CONST.R/OB.Toptv)/(OB.Hdv-OB.Hav*(1-np.exp(OB.Hav*(TEMP-OB.Toptv)/TEMP/CONST.R/OB.Toptv)))
# Jmax = OB.koptj*OB.Hdj*np.exp(OB.Haj*(TEMP-OB.Toptj)/TEMP/CONST.R/OB.Toptj)/(OB.Hdj-OB.Haj*(1-np.exp(OB.Haj*(TEMP-OB.Toptj)/TEMP/CONST.R/OB.Toptj))) 
J = (OB.kai2*PAR+Jmax-np.sqrt((OB.kai2*PAR+Jmax)**2-4*OB.kai1*OB.kai2*PAR*Jmax))/2/OB.kai1

# Terms in Penman-Monteith Equation
VPD_kPa = VPD*101.325#VPD*Psurf
sV = 0.04145*np.exp(0.06088*T_C) #in Kpa
RNg = np.array(RNET*np.exp(-LAI*VegK))
petVnum = (sV*(RNET-RNg)+1.225*1000*VPD_kPa*GA)*(RNET>0)/CONST.lambda0*60*60  #kg/s/m2/CONST.lambda0*60*60
# (sV*(rnmg-1*RNgg) + 1.225*1000*myvpd*myga)*(myrn > 0)
petVnumB = 1.26*(sV*RNg)/(sV+CONST.gammaV)/CONST.lambda0*60*60 

def advance_linearize(s2,phiL,ti,gpmax,C,psi50X,bexp,timestep):
    a = -1/(2*psi50X)
    # f_const = gpmax*(1+a*phiL)*(phi0*(s2/n)**(-bexp) - phiL)
    # f_x = gpmax*((a)*(phi0*(s2/n)**(-bexp) - phiL) + (1+a*phiL)*( - 1))
    # f_y = gpmax*(1+a*phiL)*(phi0*n**bexp*s2**(-bexp-1)*(-bexp))
    phiS2 = phi0*(s2/n)**(-bexp)
    delta_phi = phiS2 - phiL
 
    f_const = gpmax*(1+a*phiL)*delta_phi
    f_x = gpmax*(a*delta_phi + (1+a*phiL)*(-1))
    f_y = gpmax*(1+a*phiL)*(phiS2*(-bexp)/s2-phiL) # need to double check
    # f_y = gpmax*(1+a*phiL)*(phiS2*(-bexp)/s2) # need to double check
    # f_y = gpmax*(1+a*phiL)*(phi0*n**bexp*s2**(-bexp-1)*(-bexp))
    j0 = f_const - f_x*phiL - f_y*s2
    jp = f_x
    js = f_y
    k1 = jp/C - js/Z_r
    k0 = -jp/C*ti + k1*j0
    x0 = C*phiL + Z_r*s2
    xnew = -ti*timestep + x0
    y0 = jp*phiL + js*s2
    ynew = (y0 + k0/k1)*np.exp(k1*timestep) - k0/k1
    snew = (ynew - jp/C*xnew) / (-jp*Z_r/C + js)
    psiLnew = (xnew - Z_r*snew)/C
    return snew, psiLnew
 
tdiv = 3
def get_ti(clm,condS):
    RNET_i,a1_i,a2_i,Vcmax0_i,ci_i,LAI_i,petVnum_i,sV_i,GA_i = clm
    if condS>0 and RNET_i>0:
        An = max(0,min(a1_i*condS,a2_i)-0.015*Vcmax0_i*condS)
        gs = 1.6*An/(ca-ci_i)*LAI_i*0.02405
        ti = petVnum_i/(sV_i+CONST.gammaV*(1+GA_i*(1/GA_i+1/gs)))
    else: 
        ti = 0
    return ti
 
def runhh_2soil_hydro(theta):    
    g1, lpx, psi50X, gpmax,C, bexp, sbot = theta[:7]
    
    medlyn_term = 1+g1/np.sqrt(VPD_kPa) # double check
    ci = ca*(1-1/medlyn_term)
    a1 = Vcmax0*(ci-cp)/(ci + Kc*(1+209/Ko))
    a2 = J*(ci-cp)/(4*(ci + 2*cp))
    
    psi50X = -1.*psi50X
    psi50L = lpx*psi50X
    # SP = SoilPara(SR[0],SR[1],bexp,sbot)
    
    p3 = phi0_mm*(sbot/n)**(-bexp)+m3 
    k3 = ksoil*(sbot/n)**(2*bexp) 
    
    phil_list = np.zeros([N,])
    # et_list = np.zeros([N,])
    
    s1 = np.copy(sinit)
    s2 = np.copy(sinit) 
    phiL = phi0*(s2/n)**(-bexp) - 0.01
    
    s1_list = np.zeros([N,]); s2_list = np.zeros([N,])
    e_list = np.zeros([N,]); t_list = np.zeros([N,])
    
    for i in np.arange(N):

        phil_list[i] = phiL*1.0
        clm = (RNET[i],a1[i],a2[i],Vcmax0[i],ci[i],LAI[i],petVnum[i],sV[i],GA[i])
        condS = max(min(1-phiL/(2*psi50L),1),0)
        ti = get_ti(clm,condS)
        s2_pred, phiL_pred = advance_linearize(s2,phiL,ti,gpmax,C,psi50X,bexp,dt)     
        if np.abs(phiL_pred-phiL) < np.abs(psi50L):
            s2 = np.copy(s2_pred)
            phiL = np.copy(phiL_pred)
        else:
            tlist = np.zeros(tdiv)
            for subt in np.arange(tdiv):
                condS = max(min(1-phiL/(2*psi50L),1),0)
                tlist[subt] = get_ti(clm,condS)               
                s2, phiL = advance_linearize(s2,phiL,ti,gpmax,C,psi50X,bexp,dt/tdiv)
            ti = np.mean(tlist)
        
        ei= petVnumB[i]*(s1/n) #**bexp#*s1/n#*soilfac#*((s1-smcwilt)/(n-smcwilt)**(1))
        s1 = min(s1+(P[i]-ei)*dt/d1,n)#p_e = P-E 
        
              
        p1 = phi0_mm*(s1/n)**(-bexp) + m1
        p2 = phi0_mm*(s2/n)**(-bexp) + m2
        k1 = ksoil*(s1/n)**(2*bexp)
        k2 = ksoil*(s2/n)**(2*bexp)
        f12 = 2/(1/k1+1/k2) * (p1-p2) / (m1-m2)*dt
        f23 = 2/(1/k2+1/k3) * (p2-p3) / (m2-m3)*dt
        
        s1 = max(s1-f12/d1,0.05)
        s2 = min(max(s2+f12/d2 - f23/d2,0.05),n) 
    
        s1_list[i] = np.copy(s1); s2_list[i] = np.copy(s2)
        e_list[i] = np.copy(ei); t_list[i] = np.copy(ti)
        
    s1_list[np.isnan(s1_list)] = np.nanmean(s1_list); s1_list[s1_list>1] = 1; s1_list[s1_list<0] = 0
    
    return phil_list,e_list,t_list,s1_list,s2_list


dVPD = hour2day(VPD,idx)[~discard_vod][1::2]
wVPD = hour2week(VPD)[~discard_et]
hSOILM = np.zeros(VPD.shape)+np.nan
hSOILM[~np.repeat(discard_vod,4)] = np.repeat(SOILM,8)
wSOILM = hour2week(hSOILM,UNIT=1)[~discard_et]

wet = (SOILM>np.nanpercentile(SOILM,70)) & (dVPD<np.nanpercentile(dVPD,30)) # one per day
dry = (SOILM<np.nanpercentile(SOILM,30)) & (dVPD>np.nanpercentile(dVPD,70))
dwet = np.repeat(wet,2) # two per day
ddry = np.repeat(dry,2) 
wwet = (wSOILM>np.nanpercentile(wSOILM,70)) & (wVPD<np.nanpercentile(wVPD,30)) # per week
wdry = (wSOILM<np.nanpercentile(wSOILM,30)) & (wVPD>np.nanpercentile(wVPD,70))


valid_sm = ~np.isnan(SOILM); SOILM_valid = SOILM[valid_sm]
bins = np.arange(0,1.02,0.01)
counts, bin_edges = np.histogram(SOILM_valid, bins=bins, normed=True)
cdf1 = np.cumsum(counts)/sum(counts)
    
for MODE in MODE_list: 
    PREFIX = outpath+MODE+'_'+sitename+'_'
    varnames, bounds = get_var_bounds(MODE)    
    trace = GetTrace(PREFIX,varnames,0,optimal=False)
    trace = trace[trace['step']>trace['step'].max()*warmup].reset_index().drop(columns=['index'])
      
    TS = [[] for i in range(9)]
    PARA = [[] for i in range(2)]

    for count in range(nsample):
        print(count)
        idx_s = max(len(trace)-1-count*thinning,0)#randint(0,len(trace))
        try:
            tmp = trace['g1'].iloc[idx_s]
        except IndexError:
            print(trace)
            print(idx_s)
            print(sitename) 
        theta = trace.iloc[idx_s][varnames].values
        # theta  = [trace['g1'].iloc[idx_s],trace['lpx'].iloc[idx_s],trace['psi50X'].iloc[idx_s],
        #           trace['gpmax'].iloc[idx_s],trace['C'].iloc[idx_s],trace['bexp'].iloc[idx_s],trace['bc'].iloc[idx_s],
        #           trace['sigma_et'].iloc[idx_s],trace['sigma_vod'].iloc[idx_s],trace['loglik'].iloc[idx_s]]
        PSIL_hat,E_hat,T_hat,S1_hat,S2_hat = runhh_2soil_hydro(theta)
    
        
        ET_ampm = hour2day(E_hat+T_hat,[idx[1]-1,idx[1]])[~discard_vod]
        E_hat = hour2week(E_hat,UNIT=24)[~discard_et] # mm/hr -> mm/day
        T_hat = hour2week(T_hat,UNIT=24)[~discard_et]
        dPSIL = hour2day(PSIL_hat,idx)[~discard_vod]
        VOD_hat,popt = fitVOD_RMSE(dPSIL,dLAI,VOD_ma,return_popt=True) 
        dS1 = hour2day(S1_hat,idx)[~discard_vod][::2]
        dS2 = hour2day(S2_hat,idx)[~discard_vod][::2]

        if np.isfinite(np.nansum(dS1)) and np.nansum(dS1)>0:
            counts, bin_edges = np.histogram(dS1, bins=bins, normed=True)
            cdf2 = np.cumsum(counts)/sum(counts)
            dS1_matched = np.array([bin_edges[np.abs(cdf1-cdf2[int(itm*100)]).argmin()] for itm in dS1])
        else:
            dS1_matched = np.zeros(dS1.shape)+np.nan
            

        TS = [np.concatenate([TS[ii],itm]) for ii,itm in enumerate((VOD_hat,E_hat,T_hat,ET_ampm,PSIL_hat,dS1_matched,dS2))]
        PARA = [np.concatenate([PARA[ii],itm]) for ii,itm in enumerate((popt,theta))]
    
    TS = [np.reshape(itm,[nsample,-1]) for itm in TS] # VOD,E,T,ET_AP,PSIL,S1,S2
    PARA = [np.reshape(itm,[nsample,-1]) for itm in PARA]
    
   
    forwardname = forwardpath+MODE+'_'+sitename+'.pkl'
    with open(forwardname, 'wb') as f: pickle.dump((TS,PARA), f)
    
    
    # ======== OBS stats ===========
    OBS = (VOD_ma,SOILM,ET,VOD_ma[1::2]/VOD_ma[::2])
    OBS_temporal_mean = [np.nanmean(itm) for itm in OBS]
    OBS_temporal_std = [np.nanstd(itm) for itm in OBS]
    
    OBS_temporal_mean.append(np.nanmean(VOD_ma[dwet])/np.nanmean(VOD_ma[ddry]))
    OBS_temporal_std.append(np.nan)
    OBS_temporal_mean.append(np.nanmean(ET[wwet])/np.nanmean(ET[wdry]))
    OBS_temporal_std.append(np.nan)
    res = nanOLS(np.column_stack([VOD_ma[::2],dLAI[::2]]), VOD_ma[1::2])
    if res!=0:
        OBS_temporal_mean.append(res.params[0])
        OBS_temporal_std.append(res.params[0]-res.conf_int(0.32)[0,0])
    else:
        OBS_temporal_mean.append(res); OBS_temporal_std.append(res)
    obsname = statspath+'OBS_'+MODE+'_'+sitename+'.pkl'
    with open(obsname, 'wb') as f: 
        pickle.dump((OBS_temporal_mean,OBS_temporal_std), f)

    # VOD,SOILM,ET,VODr_ampm,VODr_wd,ETr_wd,ISO = OBS_temporal_mean or OBS_temporal_std
    
    
    # ========= Convergence ==========
    sample_length = int(3e3); step = int(5e2)
    st_list = range(1000,int(len(trace)/sample_length)*sample_length-sample_length+1,step)
    Geweke = []
    chainid = 0
    for varname in varnames[:-1]:
        chain = np.array(trace[varname][trace['chain']==chainid])
        chain = chain[:int(len(chain)/sample_length)*sample_length] 
        for st in st_list:
            tmps = chain[st:(st+sample_length)]
            tmpe = chain[-sample_length:]
            Geweke.append((np.nanmean(tmps)-np.nanmean(tmpe))/np.sqrt(np.nanvar(tmps)+np.nanvar(tmpe)))
    Geweke = np.abs(np.array(Geweke))
    
    # ======== Performance =========
    r2_vod = np.apply_along_axis(nancorr,1,TS[0],VOD_ma)**2
    r2_et = np.apply_along_axis(nancorr,1,TS[1]+TS[2],ET)**2
    r2_sm = np.apply_along_axis(nancorr,1,TS[5],SOILM)**2
    er2_vod = nancorr(np.nanmean(TS[0],axis=0),VOD_ma)**2
    er2_et = nancorr(np.nanmean(TS[1]+TS[2],axis=0),ET)**2
    er2_sm = nancorr(np.nanmean(TS[5],axis=0),SOILM)**2
    acc_en = [er2_vod,er2_et,er2_sm]
    p50_pct = [trace['psi50X'].quantile(pct) for pct in [.25,.5,.75]] 
    
    accname = statspath+'R2_'+MODE+'_'+sitename+'.pkl'
    with open(accname, 'wb') as f: 
        pickle.dump((acc_en,r2_vod,r2_et,r2_sm,p50_pct,Geweke), f)
    
    # ======== TS stats ============
    # np.apply_along_axis()
    TS.append(TS[0][:,1::2]/TS[0][:,::2]) # VODr_ampm, PM/AM
    TS.append(TS[3][:,1::2]/TS[3][:,::2]) # ETr_ampm  
    
    TS_temporal_mean = [np.nanmean(itm,axis=1) for itm in TS]
    TS_temporal_std = [np.nanstd(itm,axis=1) for itm in TS]
    
    TS_temporal_mean.append(np.nanmean(TS[0][:,dwet],axis=1)/np.nanmean(TS[0][:,ddry],axis=1)) #VODr_wd
    TS_temporal_std.append(np.zeros([nsample,])+np.nan)
    TS_temporal_mean.append(np.nanmean((TS[1]+TS[2])[:,wwet],axis=1)/np.nanmean((TS[1]+TS[2])[:,wdry],axis=1)) #ETr_wd
    TS_temporal_std.append(np.zeros([nsample,])+np.nan)
    
    iso_mean = []; iso_std = []
    for i in range(nsample):
        res = nanOLS(np.column_stack([TS[0][i,::2],dLAI[::2]]), TS[0][i,1::2])
        if res!=0:
            iso_mean.append(res.params[0])
            iso_std.append(res.params[0]-res.conf_int(0.32)[0,0])
        else:
            iso_mean.append(res)
            iso_std.append(res)
    
    TS_temporal_mean.append(np.array(iso_mean))
    TS_temporal_std.append(np.array(iso_std))

    PARA_ensembel_mean = [np.nanmean(itm,axis=0) for itm in PARA]
    PARA_ensembel_std = [np.nanstd(itm,axis=0) for itm in PARA]
    # VOD,E,T,ET_AP,PSIL,S1,S2,VODr_ampm, ETr_ampm, VODr_wd, ETr_wd, ISO= TS_temporal_mean or TS_temporal_std
    
    
    statsname = statspath+'TS_'+MODE+'_'+sitename+'.pkl'
    with open(statsname, 'wb') as f: 
        pickle.dump((TS_temporal_mean,TS_temporal_std,PARA_ensembel_mean,PARA_ensembel_std), f)

toc = time.perf_counter()


print(f"Running time (20 sites): {toc-tic:0.4f} seconds")



# %%
# import matplotlib.pyplot as plt
# plt.plot(VOD,'o',color='grey');plt.plot(VOD_hat,'-b')
# r2_vod = 1-np.nanmean((VOD-VOD_hat)**2)/np.nanmean((VOD-np.nanmean(VOD))**2)
# plt.figure()
# plt.plot(ET,'o',color='grey');plt.plot(ET_hat,'-b')
# r2_et = 1-np.nanmean((ET-ET_hat)**2)/np.nanmean((ET-np.nanmean(ET))**2)
# print([r2_vod,r2_et])
    # SVOD = []
    # SE = []
    # ST = []
    # SET_AP = []
    # SPSIL = []
    # SS1 = []
    # SS2 = []
    # SPOPT = []
    # STHETA = []
        # SVOD = np.concatenate([SVOD,VOD_hat])
        # SE = np.concatenate([SE,E_hat])
        # ST = np.concatenate([ST,T_hat])
        # SET_AP = np.concatenate([SET_AP,ET_ampm])
        # SPSIL = np.concatenate([SPSIL,PSIL_hat])
        # SS1 = np.concatenate([SS1,S1_hat])
        # SS2 = np.concatenate([SS2,S2_hat])
        # SPOPT = np.concatenate([SPOPT,popt])
        # STHETA = np.concatenate([STHETA,theta])
        
    
    # SVOD = np.reshape(SVOD,[nsample,-1])
    # SE = np.reshape(SE,[nsample,-1])
    # ST = np.reshape(ST,[nsample,-1])
    # SET_AP = np.reshape(SET_AP,[nsample,-1])
    # SPSIL = np.reshape(SPSIL,[nsample,-1])
    # SS1 = np.reshape(SS1,[nsample,-1])
    # SS2 = np.reshape(SS2,[nsample,-1])
    # SPOPT = np.reshape(SPOPT,[nsample,-1])
    # STHETA = np.reshape(STHETA,[nsample,-1])

