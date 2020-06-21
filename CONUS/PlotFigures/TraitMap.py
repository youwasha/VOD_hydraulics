#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May  3 19:21:28 2020

@author: yanlan
"""

import matplotlib.pyplot as plt
import pickle
import numpy as np
import pandas as pd
import seaborn as sns; sns.set(style="ticks", color_codes=True,font_scale=1.75)
import os; os.environ['PROJ_LIB'] = '/Users/yanlan/opt/anaconda3/pkgs/proj4-5.2.0-h0a44026_1/share/proj/'
from mpl_toolkits.basemap import Basemap
import sys; sys.path.append("../Utilities/")
from Utilities import LatLon
from scipy.stats import norm,gamma
parentpath = '/Volumes/ELEMENTS/VOD_hydraulics/'
versionpath = parentpath + 'Retrieval_0510/'
outpath = versionpath+'Output/'

traitpath = versionpath+'Traits/'
r2path = versionpath+'R2_test/'
npath = parentpath+'Input/ValidN/'
SiteInfo = pd.read_csv('../Utilities/SiteInfo_US_full.csv')

varlist = ['g1','lpx','psi50X','gpmax','C','bexp','bc']

MODE = 'AM_PM_ET_'

#%%
V50 = np.zeros([0,len(varlist)]); 
V25 = np.copy(V50); V75 = np.copy(V50)
HSM = np.zeros([0,3])
ML = np.zeros([0,])
    
R2 = np.zeros([0,2])
ValidN = np.zeros([len(SiteInfo),2])
for arrayid in range(14):
    print(arrayid)
    traitname = traitpath+'Traits_'+str(arrayid)+'_1E3.pkl'
    hsmname = traitpath+'HSM_'+str(arrayid)+'_1E3.pkl'
    with open(traitname, 'rb') as f: 
        Val_25, Val_50, Val_75, MissingList = pickle.load(f)
    with open(hsmname, 'rb') as f: 
       hsm = pickle.load(f)
    V25 = np.concatenate([V25,Val_25],axis=0)
    V50 = np.concatenate([V50,Val_50],axis=0)
    V75 = np.concatenate([V75,Val_75],axis=0)
    ML = np.concatenate([ML,MissingList])
    HSM = np.concatenate([HSM,np.transpose(np.array([np.nanpercentile(hsm,pct,axis=1) for pct in [25,50,75]]))],axis=0)
    
    nname = npath+'N_'+str(arrayid)+'_1E3.pkl.npy'
    vn = np.load(nname)
    array_range = np.arange(arrayid*1000,(arrayid+1)*1000)
    ValidN[array_range,:] =  vn[array_range,:]
    # plt.figure();plt.plot(vn[:,1])
    r2anme = r2path+'R2_'+str(arrayid)+'_1E3.pkl'
    with open(r2anme, 'rb') as f: 
        r2, MissingListR2 = pickle.load(f)
    R2 = np.concatenate([R2,r2],axis=0)
    
#%%
# SiteInfo = SiteInfo.iloc[0:len(V25)]
# # Trait = pd.DataFrame((V75-V25)/V50,columns=varlist)

Trait = pd.DataFrame(V50,columns=varlist)
Acc = pd.DataFrame(R2,columns=['R2_VOD','R2_ET'])
VN = pd.DataFrame(ValidN,columns=['N_VOD','N_ET'])

df = pd.concat([SiteInfo,Trait,Acc,VN],axis=1)
# df = pd.concat([SiteInfo,Trait,VN],axis=1)

# c4filter = [(igbp in [10,12]) for igbp in df['IGBP']]
# df['lcfilter'] =(np.array(c4filter)*(df['C4frac']<=0) + (df['C4frac']>50) + (df['IGBP']==11)+(df['IGBP']==0)+(df['IGBP']>12))*1# to be removed
df['obsfilter'] = (df['N_VOD']>10)*(df['N_ET']>2)*1 # to be used
df = df[df['obsfilter']==1]
# plt.hist(df['N_VOD'])
#%%
# df['lcfilter'] = ((df['IGBP']==16))*1# to be removed
# df['obsfilter'] = (df['N_VOD']>500)*(df['N_ET']>50)*1 # to be used

# df['obsfilter'][(df['N_ET']<70)*np.array([(igbp in [7,10]) for igbp in df['IGBP']])] = 0
# # plt.hist(df['N_VOD'])
# df = df[(df['lcfilter']==0)*(df['obsfilter']==1)]*1
# df = df[(df['lcfilter']==0)]*1
# df = df[df['obsfilter']==1]

# df['obsfilter'] = (df['N_VOD']>50)*(df['N_ET']>10)*1 # to be used
# df['lcfilter'] =((df['C4frac']>50) + (df['IGBP']==11)+(df['IGBP']==0)+(df['IGBP']>12))*1# to be removed

# df = df[(df['lcfilter']==0)*(df['obsfilter']==1)]*1
# df = df[(df['obsfilter']==1)]*1



# #%%
# df['empty'] = df['g1'].isna()*1
# tmpdf = df.groupby('row').agg('mean')['empty']
# print(tmpdf[tmpdf>0.8])


varname = 'R2_ET'
# varname='IGBP'
# if df[varname].mean()>0:df[varname] = -df[varname]
lat,lon = LatLon(np.array(df['row']),np.array(df['col']))
heatmap1_data = pd.pivot_table(df, values=varname, index='row', columns='col')
fig=plt.figure(figsize=(13.2,5))
m = Basemap(llcrnrlon = -128, llcrnrlat = 25, urcrnrlon = -62, urcrnrlat = 50)

m.drawcoastlines()
m.drawcountries()
mycmap = sns.cubehelix_palette(rot=-.63, as_cmap=True)
# mycmap = sns.cubehelix_palette(6, rot=-.5, dark=.3,as_cmap=True)
cs = m.pcolormesh(np.unique(lon),np.flipud(np.unique(lat)),heatmap1_data,cmap=mycmap,vmin=0,vmax=1,shading='quad')
cbar = m.colorbar(cs)
cbar.set_label(varname,rotation=360,labelpad=15)
plt.show()


#%%
trb_df = df[df['R2_ET']<0]
len(trb_df)/len(df)
trb_df.to_csv('trb_list.csv')
#%%
c4filter = [(igbp in [10,12]) for igbp in df['IGBP']]
df['lcfilter'] =(np.array(c4filter)*(df['C4frac']<=0) + (df['C4frac']>30) + (df['IGBP']==11)+(df['IGBP']==0)+(df['IGBP']>13))*1# to be removed

subset = df[(df['IGBP'].isin([1,4,6,7,8,10]))*(df['lcfilter']==0)]
# subset = df[(df['IGBP'].isin([1,4,7,8,10]))*(df['lcfilter']==0)]

IGBPlist = ['NA','ENF','EBF','DNF','DBF','DBF','Shrubland','Shrubland',
            'Savannas','Savannas','Grassland','Wetland','Cropland']

IGBP_str = [IGBPlist[itm] for itm in np.array(subset['IGBP'])]
subset['IGBP_str'] = IGBP_str
# subset  = subset[subset['R2_ET']>-1]

IGBP_list = subset['IGBP_str'].unique()
median_list = subset.groupby('IGBP_str').agg('median')[varname]
lin_list = np.array([3.97,2.35,4.5,5.76,4.22])
IGBP_list_sorted = ['ENF','DBF','Shrubland','Grassland','Savannas']

median_array = np.zeros([len(subset),])
lin_array = np.zeros([len(subset),])
for i,igbp in enumerate(list(median_list.index)):
    median_array[subset['IGBP_str']==igbp] = median_list[igbp]
    lin_array[subset['IGBP_str']==igbp] = lin_list[i]
subset['median_array'] = median_array    
subset['lin_array'] = lin_array    


plt.figure(figsize=(11,5.2))
ax1 = plt.subplot(111)
pal = sns.cubehelix_palette(rot=-.63,reverse=False)
plt.bar(0,.1,color='w',edgecolor='k',label='Retrieved median')
sns.barplot(x='IGBP_str',y=varname,ci=None,data=subset.sort_values(by=['lin_array'],ascending=True),
            estimator=np.median,palette = pal,edgecolor='k')

for i,itm in enumerate(IGBP_list_sorted):
    if i==0:
        plt.plot([i,i],[subset[varname][subset['IGBP_str']==itm].quantile(.25),subset[varname][subset['IGBP_str']==itm].quantile(.75)],'-k',label='Mid-50% range')

    else:
        plt.plot([i,i],[subset[varname][subset['IGBP_str']==itm].quantile(.25),subset[varname][subset['IGBP_str']==itm].quantile(.75)],'-k')

plt.xlabel('')
plt.ylabel(varname,rotation=360,labelpad=20)
handles, labels = ax1.get_legend_handles_labels()
plt.legend(handles[::-1], labels[::-1],loc=2,ncol=2)
plt.ylim([0,.8])




#%%
varname = 'lpx'
# varname='IGBP'
Trait = pd.DataFrame(V50,columns=varlist)
Acc = pd.DataFrame(R2,columns=['R2_VOD','R2_ET'])
VN = pd.DataFrame(ValidN,columns=['N_VOD','N_ET'])

df = pd.concat([SiteInfo,Trait,Acc,VN],axis=1)
df['obsfilter'] = (df['N_VOD']>10)*(df['N_ET']>2)*1 # to be used
df['lcfilter'] =((df['IGBP']==10))*1# to be removed
# df = df[(df['lcfilter']==0)*(df['obsfilter']==1)]*1
df = df[(df['obsfilter']==1)]*1

if df[varname].mean()>0:df[varname] = -df[varname]
lat,lon = LatLon(np.array(df['row']),np.array(df['col']))
heatmap1_data = pd.pivot_table(df, values=varname, index='row', columns='col')
fig=plt.figure(figsize=(13.2,5))
m = Basemap(llcrnrlon = -128, llcrnrlat = 25, urcrnrlon = -62, urcrnrlat = 50)

m.drawcoastlines()
m.drawcountries()
mycmap = sns.cubehelix_palette(rot=-.63, as_cmap=True,reverse=True)
# mycmap = sns.cubehelix_palette(6, rot=-.5, dark=.3,as_cmap=True)
cs = m.pcolormesh(np.unique(lon),np.flipud(np.unique(lat)),heatmap1_data,cmap=mycmap,vmin=-15,vmax=0,shading='quad')
cbar = m.colorbar(cs)
cbar.set_label(varname,rotation=360,labelpad=15)
plt.show()


c4filter = [(igbp in [10,12]) for igbp in df['IGBP']]
df['lcfilter'] =(np.array(c4filter)*(df['C4frac']<=0) + (df['C4frac']>30) + (df['IGBP']==11)+(df['IGBP']==0)+(df['IGBP']>13))*1# to be removed

subset = df[(df['IGBP'].isin([1,4,6,7,8,10]))*(df['lcfilter']==0)]
# subset = df[(df['IGBP'].isin([1,4,7,8,10]))*(df['lcfilter']==0)]

IGBPlist = ['NA','ENF','EBF','DNF','DBF','DBF','Shrubland','Shrubland',
            'Savannas','Savannas','Grassland','Wetland','Cropland']

IGBP_str = [IGBPlist[itm] for itm in np.array(subset['IGBP'])]
subset['IGBP_str'] = IGBP_str
# subset  = subset[subset['R2_ET']>-1]

IGBP_list = subset['IGBP_str'].unique()
median_list = subset.groupby('IGBP_str').agg('median')[varname]
lin_list = np.array([3.97,2.35,4.5,5.76,4.22])
IGBP_list_sorted = ['ENF','DBF','Shrubland','Grassland','Savannas']

median_array = np.zeros([len(subset),])
lin_array = np.zeros([len(subset),])
for i,igbp in enumerate(list(median_list.index)):
    median_array[subset['IGBP_str']==igbp] = median_list[igbp]
    lin_array[subset['IGBP_str']==igbp] = lin_list[i]
subset['median_array'] = median_array    
subset['lin_array'] = lin_array    


plt.figure(figsize=(11,5.2))
ax1 = plt.subplot(111)
pal = sns.cubehelix_palette(rot=-.63,reverse=False)
plt.bar(0,-.1,color='w',edgecolor='k',label='Retrieved median')
sns.barplot(x='IGBP_str',y=varname,ci=None,data=subset.sort_values(by=['lin_array'],ascending=True),
            estimator=np.median,palette = pal,edgecolor='k')

for i,itm in enumerate(IGBP_list_sorted):
    if i==0:
        plt.plot([i,i],[subset[varname][subset['IGBP_str']==itm].quantile(.25),subset[varname][subset['IGBP_str']==itm].quantile(.75)],'-k',label='Mid-50% range')

    else:
        plt.plot([i,i],[subset[varname][subset['IGBP_str']==itm].quantile(.25),subset[varname][subset['IGBP_str']==itm].quantile(.75)],'-k')

plt.xlabel('')
plt.ylabel(varname,rotation=360,labelpad=20)
handles, labels = ax1.get_legend_handles_labels()
plt.legend(handles[::-1], labels[::-1],loc=3,ncol=2)
# plt.ylim([0,1.1])

#%%
varname = 'gpmax'
# varname='IGBP'
Trait = pd.DataFrame(V50,columns=varlist)
Acc = pd.DataFrame(R2,columns=['R2_VOD','R2_ET'])
VN = pd.DataFrame(ValidN,columns=['N_VOD','N_ET'])

df = pd.concat([SiteInfo,Trait,Acc,VN],axis=1)
df['obsfilter'] = (df['N_VOD']>10)*(df['N_ET']>2)*1 # to be used
df['lcfilter'] =((df['IGBP']==10))*1# to be removed
df = df[(df['lcfilter']==0)*(df['obsfilter']==1)]*1
# df = df[(df['obsfilter']==1)]*1

lat,lon = LatLon(np.array(df['row']),np.array(df['col']))
heatmap1_data = pd.pivot_table(df, values=varname, index='row', columns='col')
fig=plt.figure(figsize=(13.2,5))
m = Basemap(llcrnrlon = -128, llcrnrlat = 25, urcrnrlon = -62, urcrnrlat = 50)

m.drawcoastlines()
m.drawcountries()
mycmap = sns.cubehelix_palette(rot=-.63, as_cmap=True,reverse=False)
# mycmap = sns.cubehelix_palette(6, rot=-.5, dark=.3,as_cmap=True)
cs = m.pcolormesh(np.unique(lon),np.flipud(np.unique(lat)),heatmap1_data,cmap=mycmap,vmin=0,vmax=10,shading='quad')
cbar = m.colorbar(cs)
cbar.set_label(varname,rotation=360,labelpad=15)
plt.show()


c4filter = [(igbp in [10,12]) for igbp in df['IGBP']]
df['lcfilter'] =(np.array(c4filter)*(df['C4frac']<=0) + (df['C4frac']>30) + (df['IGBP']==11)+(df['IGBP']==0)+(df['IGBP']>13))*1# to be removed

subset = df[(df['IGBP'].isin([1,4,6,7,8,10]))*(df['lcfilter']==0)]
# subset = df[(df['IGBP'].isin([1,4,7,8,10]))*(df['lcfilter']==0)]

IGBPlist = ['NA','ENF','EBF','DNF','DBF','DBF','Shrubland','Shrubland',
            'Savannas','Savannas','Grassland','Wetland','Cropland']

IGBP_str = [IGBPlist[itm] for itm in np.array(subset['IGBP'])]
subset['IGBP_str'] = IGBP_str
# subset  = subset[subset['R2_ET']>-1]

IGBP_list = subset['IGBP_str'].unique()
median_list = subset.groupby('IGBP_str').agg('median')[varname]
lin_list = np.array([3.97,2.35,4.5,5.76,4.22])
IGBP_list_sorted = ['ENF','DBF','Shrubland','Grassland','Savannas']

median_array = np.zeros([len(subset),])
lin_array = np.zeros([len(subset),])
for i,igbp in enumerate(list(median_list.index)):
    median_array[subset['IGBP_str']==igbp] = median_list[igbp]
    lin_array[subset['IGBP_str']==igbp] = lin_list[i]
subset['median_array'] = median_array    
subset['lin_array'] = lin_array    


plt.figure(figsize=(11,5.2))
ax1 = plt.subplot(111)
pal = sns.cubehelix_palette(rot=-.63,reverse=False)
plt.bar(0,.1,color='w',edgecolor='k',label='Retrieved median')
sns.barplot(x='IGBP_str',y=varname,ci=None,data=subset.sort_values(by=['lin_array'],ascending=True),
            estimator=np.median,palette = pal,edgecolor='k')

for i,itm in enumerate(IGBP_list_sorted):
    if i==0:
        plt.plot([i,i],[subset[varname][subset['IGBP_str']==itm].quantile(.25),subset[varname][subset['IGBP_str']==itm].quantile(.75)],'-k',label='Mid-50% range')

    else:
        plt.plot([i,i],[subset[varname][subset['IGBP_str']==itm].quantile(.25),subset[varname][subset['IGBP_str']==itm].quantile(.75)],'-k')

plt.xlabel('')
plt.ylabel(varname,rotation=360,labelpad=20)
handles, labels = ax1.get_legend_handles_labels()
plt.legend(handles[::-1], labels[::-1],loc=1,ncol=2)
# plt.ylim([0,1.1])

#%%
varname = 'HSM75'
# varname='IGBP'
Trait = pd.DataFrame(V50,columns=varlist)
Acc = pd.DataFrame(R2,columns=['R2_VOD','R2_ET'])
VN = pd.DataFrame(ValidN,columns=['N_VOD','N_ET'])
HSM = pd.DataFrame(HSM,columns=['HSM25','HSM50','HSM75'])
df = pd.concat([SiteInfo,Trait,Acc,VN,HSM],axis=1)
df['dHSM'] = df['HSM75']-df['HSM25']
df['obsfilter'] = (df['N_VOD']>10)*(df['N_ET']>2)*1 # to be used
df['lcfilter'] =((df['IGBP']==10))*1# to be removed
df = df[(df['lcfilter']==0)*(df['obsfilter']==1)]*1
# df = df[(df['obsfilter']==1)]*1

lat,lon = LatLon(np.array(df['row']),np.array(df['col']))
heatmap1_data = pd.pivot_table(df, values=varname, index='row', columns='col')
fig=plt.figure(figsize=(13.2,5))
m = Basemap(llcrnrlon = -128, llcrnrlat = 25, urcrnrlon = -62, urcrnrlat = 50)

m.drawcoastlines()
m.drawcountries()
mycmap = sns.cubehelix_palette(rot=-.63, as_cmap=True,reverse=False)
# mycmap = sns.cubehelix_palette(6, rot=-.5, dark=.3,as_cmap=True)
cs = m.pcolormesh(np.unique(lon),np.flipud(np.unique(lat)),heatmap1_data,cmap=mycmap,vmin=0,vmax=8,shading='quad')
cbar = m.colorbar(cs)
cbar.set_label(varname,rotation=360,labelpad=15)
plt.show()


c4filter = [(igbp in [10,12]) for igbp in df['IGBP']]
df['lcfilter'] =(np.array(c4filter)*(df['C4frac']<=0) + (df['C4frac']>30) + (df['IGBP']==11)+(df['IGBP']==0)+(df['IGBP']>13))*1# to be removed

subset = df[(df['IGBP'].isin([1,4,6,7,8,10]))*(df['lcfilter']==0)]
# subset = df[(df['IGBP'].isin([1,4,7,8,10]))*(df['lcfilter']==0)]

IGBPlist = ['NA','ENF','EBF','DNF','DBF','DBF','Shrubland','Shrubland',
            'Savannas','Savannas','Grassland','Wetland','Cropland']

IGBP_str = [IGBPlist[itm] for itm in np.array(subset['IGBP'])]
subset['IGBP_str'] = IGBP_str
# subset  = subset[subset['R2_ET']>-1]

IGBP_list = subset['IGBP_str'].unique()
median_list = subset.groupby('IGBP_str').agg('median')[varname]
lin_list = np.array([3.97,2.35,4.5,5.76,4.22])
IGBP_list_sorted = ['ENF','DBF','Shrubland','Grassland','Savannas']

median_array = np.zeros([len(subset),])
lin_array = np.zeros([len(subset),])
for i,igbp in enumerate(list(median_list.index)):
    median_array[subset['IGBP_str']==igbp] = median_list[igbp]
    lin_array[subset['IGBP_str']==igbp] = lin_list[i]
subset['median_array'] = median_array    
subset['lin_array'] = lin_array    


plt.figure(figsize=(11,5.2))
ax1 = plt.subplot(111)
pal = sns.cubehelix_palette(rot=-.63,reverse=False)
plt.bar(0,.1,color='w',edgecolor='k',label='Retrieved median')
sns.barplot(x='IGBP_str',y=varname,ci=None,data=subset.sort_values(by=['lin_array'],ascending=True),
            estimator=np.median,palette = pal,edgecolor='k')

for i,itm in enumerate(IGBP_list_sorted):
    if i==0:
        plt.plot([i,i],[subset[varname][subset['IGBP_str']==itm].quantile(.25),subset[varname][subset['IGBP_str']==itm].quantile(.75)],'-k',label='Mid-50% range')

    else:
        plt.plot([i,i],[subset[varname][subset['IGBP_str']==itm].quantile(.25),subset[varname][subset['IGBP_str']==itm].quantile(.75)],'-k')

plt.xlabel('')
plt.ylabel(varname,rotation=360,labelpad=20)
handles, labels = ax1.get_legend_handles_labels()
plt.legend(handles[::-1], labels[::-1],loc=1,ncol=2)
# plt.ylim([0,1.1]
#%%
# import basemap
varname = 'g1'
lat,lon = LatLon(np.array(df['row']),np.array(df['col']))
heatmap1_data = pd.pivot_table(df, values=varname, index='row', columns='col')

fig=plt.figure(figsize=(13.2,5))
m = Basemap(llcrnrlon = -128, llcrnrlat = 25, urcrnrlon = -62, urcrnrlat = 50)

m.drawcoastlines()
m.drawcountries()
mycmap = sns.cubehelix_palette(rot=-.63, as_cmap=True)
# mycmap = sns.cubehelix_palette(6, rot=-.5, dark=.3,as_cmap=True)
cs = m.pcolormesh(np.unique(lon),np.flipud(np.unique(lat)),heatmap1_data,cmap=mycmap,vmin=0,vmax=9,shading='quad')
cbar = m.colorbar(cs,ticks=[0,2,4,6,8])
# cbar.set_label(r'$g_1$',rotation=360,labelpad=15)
plt.show()

#%%
# df['R2_ET'][df['R2_ET']<0] = 0
# subset = df[df['IGBP'].isin([1,4,6,7,8,10,12])*(df['R2_ET']>-0.5)*(df['R2_VOD']>-0.5)]
c4filter = [(igbp in [10,12]) for igbp in df['IGBP']]
df['lcfilter'] =(np.array(c4filter)*(df['C4frac']<=0) + (df['C4frac']>30) + (df['IGBP']==11)+(df['IGBP']==0)+(df['IGBP']>12))*1# to be removed

subset = df[(df['IGBP'].isin([1,4,6,7]))*(df['lcfilter']==0)]

IGBPlist = ['NA','ENF','EBF','DNF','DBF','DBF','Shrublands','Shrublands',
            'Savannas','Savannas','Grassland','Wetland','Cropland']

IGBP_str = [IGBPlist[itm] for itm in np.array(subset['IGBP'])]
subset['IGBP_str'] = IGBP_str

IGBP_list = subset['IGBP_str'].unique()
median_list = subset.groupby('IGBP_str').agg('median')['g1']
lin_list = np.array([3.97,2.35,4.5])

IGBP_list_sorted = np.array(median_list.index)[np.argsort(lin_list)]

median_array = np.zeros([len(subset),])
lin_array = np.zeros([len(subset),])
for i,igbp in enumerate(list(median_list.index)):
    median_array[subset['IGBP_str']==igbp] = median_list[igbp]
    lin_array[subset['IGBP_str']==igbp] = lin_list[i]
subset['median_array'] = median_array    
subset['lin_array'] = lin_array


plt.figure(figsize=(6,5))
ax1 = plt.subplot(111)
# pal = sns.cubehelix_palette(6, rot=-.5, dark=.3)
pal = sns.cubehelix_palette(rot=-.63,reverse=False)

plt.bar(0,1,color='w',edgecolor='k',label='Retrieved median')

sns.barplot(x='IGBP_str',y='g1',ci=None,data=subset.sort_values(by=['lin_array'],ascending=True),
            estimator=np.median,palette = pal,edgecolor='k')

for i,itm in enumerate(IGBP_list_sorted):
    if i==0:
        plt.plot(i,np.sort(lin_list)[i],'^r',markersize=10,label='Estimates by Lin et al.')
        plt.plot([i,i],[subset[varname][subset['IGBP_str']==itm].quantile(.25),subset[varname][subset['IGBP_str']==itm].quantile(.75)],'-k',label='Mid-50% range')

    else:
        plt.plot(i,np.sort(lin_list)[i],'^r',markersize=10)
        plt.plot([i,i],[subset[varname][subset['IGBP_str']==itm].quantile(.25),subset[varname][subset['IGBP_str']==itm].quantile(.75)],'-k')
# sns.violinplot(x='IGBP_str',y='g1',data=subset.sort_values(by=['lin_array'],ascending=True),cut=cut,palette=pal,inner=None)
# for i,itm in enumerate(IGBP_list_sorted):
#     plt.plot(i,subset[varname][subset['IGBP_str']==itm].median(),'or')
# plt.ylim(vlim+max(vlim)*np.array([-0.1,0.1]))
plt.xlabel('')
plt.ylabel(r'$g_1$',rotation=360,labelpad=20)
handles, labels = ax1.get_legend_handles_labels()
plt.legend(handles[::-1], labels[::-1],loc=2)

# plt.legend(handles[::-1], labels[::-1],loc=2,bbox_to_anchor=(0.0,1.4))
# 

