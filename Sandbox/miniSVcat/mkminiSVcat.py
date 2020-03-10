'''
script puts together full files for type, tile, night to be edited below
'''

from astropy.table import Table, join,unique,vstack
import numpy as np
import fitsio
from matplotlib import pyplot as plt

minisvdir = '/project/projectdirs/desi/users/ajross/catalogs/minisv2/'
dirout = minisvdir+'LSScats/'
randir = minisvdir+'random/'
fatype = 'non_restricted_positioners/'
tardir = minisvdir+'targets/'+fatype

type = 'ELG'
if type == 'LRG':
	bit = 53
	pr = 4000
if type == 'QSO':
	bit = 55
	pr = 10000
if type == 'ELG':
	bit = 54
	pr = 10000
	
tile = 70005
#night = '20200219'
night = '20200303'
coaddir = '/global/cfs/cdirs/desi/spectro/redux/minisv2/tiles/'
#elgandlrgbits = [1,5,6,7,8,9,11,12,13]

#if tile == 70004 and night == '20200219':
#	id4coord = '00051002' #this is the exposure ID for 70004 for the coordinates file for getting the actual hardware performance; hopefully not necessary in future
#if tile == 70003 and night == '20200219':
#	id4coord = '00051073' #this is the config for 70003
#if tile == 70002 and night == '20200304':
#	id4coord = '00053122'
#if tile == 70005 and night == '20200303':
#	id4coord = '00052978'

#get hardware info, not needed anymore because of fibermap info?
#cf = fitsio.read('/global/cfs/cdirs/desi/spectro/data/'+night+'/'+id4coord+'/coordinates-'+id4coord+'.fits')
#cloc = cf['PETAL_LOC']*1000 + cf['DEVICE_LOC']
#wpos = cf['FLAGS_EXP_2'] == 4
#print('there were '+str(len(cloc[wpos]))+' positioners that could reach their targets on '+night )
#wspec = np.isin(cf['PETAL_LOC'],specs)
#wps = wpos & wspec
#print(str(len(cloc[wps]))+' of these went to the working spectrographs ('+str(specs)+')' )
#goodloc = cloc[wps]

#put data from different spectrographs together, one table for fibermap, other for z
specs = []
#find out which spectrograph have data
for si in range(0,10):
	try:
		fitsio.read(coaddir+str(tile)+'/'+night+'/zbest-'+str(si)+'-'+str(tile)+'-'+night+'.fits')
		specs.append(si)
	except:
		print('no spectrograph '+str(si)+ ' on night '+night)
print('spectrographs with data:')
print(specs)			
tspec = Table.read(coaddir+str(tile)+'/'+night+'/zbest-'+str(specs[0])+'-'+str(tile)+'-'+night+'.fits',hdu='ZBEST')
tf = Table.read(coaddir+str(tile)+'/'+night+'/zbest-'+str(specs[0])+'-'+str(tile)+'-'+night+'.fits',hdu='FIBERMAP')
for i in range(1,len(specs)):
    tn = Table.read(coaddir+str(tile)+'/'+night+'/zbest-'+str(specs[i])+'-'+str(tile)+'-'+night+'.fits',hdu='ZBEST')
    tnf = Table.read(coaddir+str(tile)+'/'+night+'/zbest-'+str(specs[i])+'-'+str(tile)+'-'+night+'.fits',hdu='FIBERMAP')
    tspec = vstack([tspec,tn])
    tf = vstack([tf,tnf])

wloc = tf['FIBERSTATUS'] == 0
goodloc = tf[wloc]['LOCATION']
print(str(len(goodloc)) + ' locations with FIBERSTATUS 0')

pdict = dict(zip(tf['LOCATION'], tf['PRIORITY'])) #to be used later for randoms


#get target info
tfa = Table.read(tardir+'/fiberassign-0'+str(tile)+'.fits',hdu='FAVAIL')
tft = unique(tfa,keys=['TARGETID'])
wgt = (np.isin(tfa['LOCATION'],goodloc)) 
print('comparison of number targets, number of targets with good locations')
print(len(tfa),len(tfa[wgt]))
tfa = unique(tfa[wgt],keys=['TARGETID'])

print(str(len(tfa)) +' unique targets with good locations and '+str(len(tft))+ 'unique targets and unique locations '+str(len(np.unique(tft['LOCATION']))))
mtlf = tardir+'MTL_Tile_'+str(tile)+'_0.36.0_all.fits'
tt = Table.read(mtlf)
wtype = ((tt['CMX_TARGET'] & 2**bit) > 0)
tt = tt[wtype]
tfa = join(tfa,tt,keys=['TARGETID'])
tft = join(tft,tt,keys=['TARGETID'])
print(str(len(tfa)) +' unique '+type+' targets with good locations and '+str(len(tft))+ ' at '+str(len(np.unique(tfa['LOCATION'])))+' unique locations and unique targets and unique locations '+str(len(np.unique(tft['LOCATION']))))
print(len(np.unique(tfa['TARGETID'])))

#keep = (tfa['NOBS_G']>0) & (tfa['NOBS_R']>0) & (tfa['NOBS_Z']>0)
#for biti in elgandlrgbits:
#	keep &= ((tfa['MASKBITS'] & 2**biti)==0)
#tfa = tfa[keep]
#print(str(len(tfa)) +' unique targets with good locations after imaging veto' )

#Mark targets that actually got assigned fibers
tfall = Table.read(tardir+'/fiberassign-0'+str(tile)+'.fits',hdu='FIBERASSIGN')
tfall.keep_columns(['TARGETID','LOCATION'])
tfa = join(tfa,tfall,keys=['TARGETID'],join_type='left',table_names = ['', '_ASSIGNED'], uniq_col_name='{col_name}{table_name}')
#print(tfa.dtype.names)
wal = tfa['LOCATION_ASSIGNED']*0 == 0
print('number of assigned fibers '+str(len(tfa[wal])))
tfa['LOCATION_ASSIGNED'] = np.zeros(len(tfa),dtype=int)
tfa['LOCATION_ASSIGNED'][wal] = 1
wal = tfa['LOCATION_ASSIGNED'] == 1
print('number of assigned fibers '+str(len(tfa[wal])))



#whploc = tf['PRIORITY'] > pr
#hploc = tf['LOCATION'][whploc]
#whp = np.isin(tfa['LOCATION'],hploc)
#tfa = tfa[~whp]
#print(str(len(tfa)) +' unique targets with good locations after vetoing high priority' )

#select target class
wt = tf['CMX_TARGET'] & 2**bit > 0
#select good redshifts
#wtz = wt & (tspec['ZWARN'] == 0) & (np.isin(tf['LOCATION'],goodloc))
wtz = wt & (np.isin(tf['LOCATION'],goodloc))
print('there are '+str(len(tspec[wtz]))+' '+type+' targets observed on good positioners on tile '+str(tile) +' observed on '+night)
wtzg = wtz & (tspec['ZWARN'] == 0)
print('there are '+str(len(tspec[wtzg]))+' '+type+' good redshifts on tile '+str(tile) +' observed on '+night)


#tout = join(tfa,tspec[wtz],keys=['TARGETID'],join_type='left')
tout = join(tfa,tspec,keys=['TARGETID'],join_type='left')
wz = tout['ZWARN']*0 == 0
print('there are '+str(len(tout[wz]))+' rows with defined redshifts')
#tout['RA'] = tf[wtz]['TARGET_RA']
#tout['DEC'] = tf[wtz]['TARGET_DEC']
#tout['Z'] = tspec[wtz]['Z']

fout = dirout+type+str(tile)+'_'+night+'_full.dat.fits'
tout.write(fout,format='fits', overwrite=True) 
print('wrote results to '+fout)

#randoms

ranf = randir+'fba-0'+str(tile)+'.fits'
f1 = fitsio.read(ranf)
f2 = fitsio.read(ranf,ext=2)
f3 = fitsio.read(ranf,ext=3)

goodranw = np.isin(f3['LOCATION'],goodloc)
goodranid = np.unique(f3[goodranw]['TARGETID'])

t2 = Table.read(ranf,hdu=2)
tj = Table()
tj['TARGETID'] = f3[goodranw]['TARGETID']
tj['LOCATION'] = f3[goodranw]['LOCATION']
tj['FIBER'] = f3[goodranw]['FIBER']
tj = unique(tj,keys=['TARGETID'])
t2.remove_columns(['NUMOBS_MORE','PRIORITY','OBSCONDITIONS','SUBPRIORITY'])
rant = join(tj,t2,keys=['TARGETID'],join_type='left')

#now match back to randoms with all columns

tall = Table.read(randir+'tilenofa-'+str(tile)+'.fits')
tall.remove_columns(['NUMOBS_MORE','PRIORITY','OBSCONDITIONS','SUBPRIORITY','NUMOBS_INIT'])

ranall = join(rant,tall,keys=['TARGETID'],join_type='left')
#keep = (ranall['NOBS_G']>0) & (ranall['NOBS_R']>0) & (ranall['NOBS_Z']>0)
#for bit in elgandlrgbits:
#	keep &= ((ranall['MASKBITS'] & 2**bit)==0)
#print(len(ranall))
#ranall = ranall[keep]
print(len(ranall))

#plt.plot(ranall['TARGET_RA'],ranall['TARGET_DEC'],'k,')
#plt.plot(cf[wps]['TARGET_RA'],cf[wps]['TARGET_DEC'],'g.')
#plt.plot(tout['RA'],tout['DEC'],'b.',linewidth=1)
#wp = tout['Z']*0 == 0
#plt.plot(tout[wp]['RA'],tout[wp]['DEC'],'r.',linewidth=1)
#plt.show()

wz = (tout['ZWARN'] == 0) 
gz = tout[wz]['Z']
ranall['Z'] = np.ones(len(ranall))
for i in range(0,len(ranall)):
	ran = np.random.random()
	ind = int(ran*len(gz))
	ranall['Z'][i] = gz[ind]
ranall['PRIORITY'] = np.vectorize(pdict.__getitem__)(ranall['LOCATION'])
wpr = ranall['PRIORITY'] <= pr
plt.plot(ranall['TARGET_RA'],ranall['TARGET_DEC'],'k,')
plt.plot(ranall[wpr]['TARGET_RA'],ranall[wpr]['TARGET_DEC'],'r,')
plt.show()

fout = dirout+type+str(tile)+'_'+night+'_full.ran.fits'
ranall.write(fout,format='fits', overwrite=True) 
print('wrote randoms to '+fout)


