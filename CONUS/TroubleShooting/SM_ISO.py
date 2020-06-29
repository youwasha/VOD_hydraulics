#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 27 22:57:55 2020

@author: yanlan

Same as SMassim but added one parameter evk

"""



import os
import numpy as np
import pandas as pd
from scipy.stats import norm
import warnings; warnings.simplefilter("ignore")
import time
import sys; sys.path.append("../Utilities/")
from newfun_ts_slope import readCLM, fitVOD_RMSE, AMIS
from newfun_ts_slope import varnames,scale,dt, hour2day, hour2week
from newfun_ts_slope import OB,CONST,CLAPP,ca
from Utilities import MovAvg
# np.random.seed(seed=123)

# import matplotlib.pyplot as plt
# =========================== control pannel =============================
# parentpath = '/scratch/users/yanlan/'
# baseid = 0 # int(sys.argv[1])
# arrayid = int(os.environ['SLURM_ARRAY_TASK_ID'])+baseid*1000 # 0-999
# samplenum = (10,2000)

parentpath = '/Volumes/ELEMENTS/VOD_hydraulics/'
arrayid = 1
samplenum = (1,10) # number of chuncks, number of samples per chunck


versionpath = parentpath+'TroubleShooting/SM_ISO/'
inpath = parentpath+'Input/'
outpath = versionpath+'Output/'
MODE = 'AM_PM_ET'


chains_per_site = 1

fid = arrayid*1
chainid = int(fid-fid*chains_per_site)
SiteInfo = pd.read_csv('SiteInfo_reps.csv')
sitename = str(SiteInfo['row'][fid])+'_'+str(SiteInfo['col'][fid])
PREFIX = outpath+MODE+'_'+sitename+'_'+str(chainid).zfill(2)
print(PREFIX)

# =========================== read input =================================
#%%
Forcings,VOD,SM,ET,dLAI,discard_vod,discard_et,idx = readCLM(inpath,sitename)

VOD_ma = np.reshape(VOD,[-1,2])
VOD_ma = np.reshape(np.column_stack([MovAvg(VOD_ma[:,0],4),MovAvg(VOD_ma[:,1],4)]),[-1,])


Z_r,tx = (SiteInfo['Root depth'][fid]*1000,int(SiteInfo['Soil texture'][fid]))

# Z_r = 3120
# psi0cm = 48
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

#%% Calculations not affected by MCMC paramteres
RNET,TEMP,P,VPD,Psurf,GA,LAI,VegK = Forcings

N = len(RNET)
# Terms in Farquhar's model of biochemical demand for CO2
PAR = RNET/(CONST.Ephoton*CONST.NA)*1e6
T_C = TEMP-CONST.U3 # degree C
Kc = 300*np.exp(0.074*(T_C-25)) # umol/mol
Ko = 300*np.exp(0.015*(T_C-25)) # mmol/mol
cp = 36.9+1.18*(T_C-25)+0.036*(T_C-25)**2
Vcmax25 = SiteInfo['Vcmax25'][fid]
# Jmax25 = np.exp(1)*Vcmax25
# Vcmax0 = Vcmax25*np.exp(0.88*(T_C-25))/(1+np.exp(0.29*(T_C-41))) 
Vcmax0 = Vcmax25*np.exp(50*(TEMP-298)/(298*CONST.R*TEMP)) 
Jmax = Vcmax0*np.exp(1)
# Vcmax0 = OB.koptv*OB.Hdv*np.exp(OB.Hav*(TEMP-OB.Toptv)/TEMP/CONST.R/OB.Toptv)/(OB.Hdv-OB.Hav*(1-np.exp(OB.Hav*(TEMP-OB.Toptv)/TEMP/CONST.R/OB.Toptv)))
# Jmax = OB.koptj*OB.Hdj*np.exp(OB.Haj*(TEMP-OB.Toptj)/TEMP/CONST.R/OB.Toptj)/(OB.Hdj-OB.Haj*(1-np.exp(OB.Haj*(TEMP-OB.Toptj)/TEMP/CONST.R/OB.Toptj))) 
J = (OB.kai2*PAR+Jmax-np.sqrt((OB.kai2*PAR+Jmax)**2-4*OB.kai1*OB.kai2*PAR*Jmax))/2/OB.kai1

# Terms in Penman-Monteith Equation
VPD_kPa = VPD*Psurf
sV = 0.04145*np.exp(0.06088*T_C) #in Kpa
RNg = np.array(RNET*np.exp(-LAI*VegK))
petVnum = (sV*(RNET-RNg)+1.225*1000*VPD_kPa*GA)*(RNET>0)/CONST.lambda0*60*60  #kg/s/m2/CONST.lambda0*60*60
# (sV*(rnmg-1*RNgg) + 1.225*1000*myvpd*myga)*(myrn > 0)
petVnumB = 1.26*(sV*RNg)/(sV+CONST.gammaV)/CONST.lambda0*60*60 

#%%
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
    g1, lpx, psi50X, gpmax,C, bexp, sbot, evk = theta[:8]
    
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
    et_list = np.zeros([N,])

    s1 = np.copy(sinit)
    s2 = np.copy(sinit) 
    phiL = phi0*(s2/n)**(-bexp) - 0.01
    
    s1_list = np.zeros([N,])#; s2_list = np.zeros([N,])
    # e_list = np.zeros([N,]); t_list = np.zeros([N,])

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
        
        ei= petVnumB[i]*((s1-0.05)*evk) #**bexp#*s1/n#*soilfac#*((s1-smcwilt)/(n-smcwilt)**(1))
        s1 = min(s1+(P[i]-ei)*dt/d1,n)#p_e = P-E 
        
              
        p1 = phi0_mm*(s1/n)**(-bexp) + m1
        p2 = phi0_mm*(s2/n)**(-bexp) + m2
        k1 = ksoil*(s1/n)**(2*bexp)
        k2 = ksoil*(s2/n)**(2*bexp)
        f12 = 2/(1/k1+1/k2) * (p1-p2) / (m1-m2)*dt
        f23 = 2/(1/k2+1/k3) * (p2-p3) / (m2-m3)*dt
        s1 = max(s1-f12/d1,0.05)
        s2 = min(max(s2+f12/d2 - f23/d2,0.05),n)  
            
        et_list[i] = ei+ti
        s1_list[i] = np.copy(s1)#; s2_list[i] = np.copy(s2)
        # e_list[i] = np.copy(ei); t_list[i] = np.copy(ti)
    
    return phil_list,et_list,s1_list #,s1_list,s2_list,e_list,t_list

#%%
from Utilities import nanOLS
valid_vod = ~np.isnan(VOD_ma)
valid_et = ~np.isnan(ET)
valid_sm = ~np.isnan(SM)
res = nanOLS(np.column_stack([VOD_ma[::2],dLAI[::2]]), VOD_ma[1::2])
iso_flag = 1

if res!=0: iso = res.params[0]
else: iso_flag = 0

#%%
# ========================== MCMC sampling ==============================  
idx_sigma_vod = varnames.index('sigma_vod')
idx_sigma_et = varnames.index('sigma_et')
idx_sigma_sm =  varnames.index('sigma_sm')
if iso_flag>0:
    def Gaussian_loglik(theta0):
        theta = theta0*scale
        PSIL_hat,ET_hat,SM_hat = runhh_2soil_hydro(theta)
        ET_hat = hour2week(ET_hat,UNIT=24)[~discard_et] # mm/hr -> mm/day
        dPSIL = hour2day(PSIL_hat,idx)[~discard_vod]
        SM_hat = hour2day(SM_hat,idx)[~discard_vod][::2]
        VOD_hat = fitVOD_RMSE(dPSIL,dLAI,VOD_ma)
        sigma_VOD, sigma_ET, sigma_SM = (theta[idx_sigma_vod], theta[idx_sigma_et],theta[idx_sigma_sm])
    
        loglik_vod = np.nanmean(norm.logpdf(VOD_ma[valid_vod],VOD_hat[valid_vod],sigma_VOD))
        loglik_et = np.nanmean(norm.logpdf(ET[valid_et],ET_hat[valid_et],sigma_ET))
        loglik_sm = np.nanmean(norm.logpdf(SM[valid_sm],SM_hat[valid_sm],sigma_SM))
        if ~np.isfinite(loglik_vod): loglik_vod = -9999
        if ~np.isfinite(loglik_et): loglik_et = -9999
        if ~np.isfinite(loglik_sm): loglik_sm = -9999
        
        res = nanOLS(np.column_stack([VOD_hat[::2],dLAI[::2]]), VOD_hat[1::2])
        if res!=0: 
            iso_hat = res.params[0]
            iso_flag = 1
        else: 
            iso_hat = 0; iso_flag = 0
        loglik_iso = norm.logpdf(iso,iso_hat,iso*0.3)
        
        return loglik_vod+loglik_et+loglik_sm+loglik_iso*iso_flag
else:
    def Gaussian_loglik(theta0):
        theta = theta0*scale
        PSIL_hat,ET_hat,SM_hat = runhh_2soil_hydro(theta)
        ET_hat = hour2week(ET_hat,UNIT=24)[~discard_et] # mm/hr -> mm/day
        dPSIL = hour2day(PSIL_hat,idx)[~discard_vod]
        SM_hat = hour2day(SM_hat,idx)[~discard_vod][::2]
        VOD_hat = fitVOD_RMSE(dPSIL,dLAI,VOD_ma)
        sigma_VOD, sigma_ET, sigma_SM = (theta[idx_sigma_vod], theta[idx_sigma_et],theta[idx_sigma_sm])
    
        loglik_vod = np.nanmean(norm.logpdf(VOD_ma[valid_vod],VOD_hat[valid_vod],sigma_VOD))
        loglik_et = np.nanmean(norm.logpdf(ET[valid_et],ET_hat[valid_et],sigma_ET))
        loglik_sm = np.nanmean(norm.logpdf(SM[valid_sm],SM_hat[valid_sm],sigma_SM))
        if ~np.isfinite(loglik_vod): loglik_vod = -9999
        if ~np.isfinite(loglik_et): loglik_et = -9999
        if ~np.isfinite(loglik_sm): loglik_sm = -9999
        return loglik_vod+loglik_et+loglik_sm

tic = time.perf_counter()
AMIS(Gaussian_loglik,PREFIX,samplenum)
toc = time.perf_counter()
print(f"Sampling time (10 samples): {toc-tic:0.4f} seconds")

#%%
# g1, lpx, psi50X, gpmax,C, bexp, sbot = theta
# import matplotlib.pyplot as plt
# theta = [1.5,0.7,8,0.2,1,6,0.3]
# phil_list,et_list = runhh_2soil_hydro(theta)

# plt.figure();plt.plot(phil_list);plt.ylabel('psil')
# plt.figure();plt.plot(et_list);plt.ylabel('et')

# plt.figure();plt.plot(t_list);plt.ylabel('t')
# plt.figure();plt.plot(s1_list);plt.ylabel('s1')
# plt.figure();plt.plot(s2_list);plt.ylabel('s2')