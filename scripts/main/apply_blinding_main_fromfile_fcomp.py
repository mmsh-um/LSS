#standard python
'''
Documentation needs to be updated
EXAMPLE USE
===========



GENERAL NOTES
=============


NOTES FOR TESTING AND VALIDATION
================================

'''

import sys
import os
import shutil
import unittest
from datetime import datetime
import json
import numpy as np
#from numpy.random import MT19937
#from numpy.random import RandomState, SeedSequence
from numpy.random import random
import fitsio
import glob
import argparse
from astropy.io import fits
from astropy.table import Table,join,unique,vstack
from matplotlib import pyplot as plt

import LSS.main.cattools as ct
from LSS.globals import main
import LSS.blinding_tools as blind

import LSS.common_tools as common

from cosmoprimo.fiducial import DESI
from cosmoprimo.utils import DistanceToRedshift
from cosmoprimo import Cosmology


if os.environ['NERSC_HOST'] == 'cori':
    scratch = 'CSCRATCH'
elif os.environ['NERSC_HOST'] == 'perlmutter':
    scratch = 'PSCRATCH'
else:
    print('NERSC_HOST is not cori or permutter but is '+os.environ['NERSC_HOST'])
    sys.exit('NERSC_HOST not known (code only works on NERSC), not proceeding') 


parser = argparse.ArgumentParser()
parser.add_argument("--type", help="tracer type to be selected")
parser.add_argument("--basedir_in", help="base directory for input, default is location for official catalogs",default='/global/cfs/cdirs/desi/survey/catalogs/')
parser.add_argument("--basedir_out", help="base directory for output, default is C(P)SCRATCH",default=os.environ[scratch])
parser.add_argument("--version", help="catalog version",default='test')
parser.add_argument("--survey", help="e.g., main (for all), DA02, any future DA",default='Y1')
parser.add_argument("--verspec",help="version for redshifts",default='iron')
parser.add_argument("--notqso",help="if y, do not include any qso targets",default='n')
parser.add_argument("--reg_md",help="whether to run on split N/S or NGC/SGC",default='NS')

parser.add_argument("--split_GC",help="whether to make the split NGC/SGC",default='n')

parser.add_argument("--get_par_mode",help="how to get the row of the file with w0/wa values",choices=['random', 'from_file'],default='random')

parser.add_argument("--baoblind",help="if y, do the bao blinding shift",default='n')
parser.add_argument("--mkclusdat",help="if y, make the clustering data files after the BAO blinding (needed for RSD blinding)",default='n')
parser.add_argument("--mkclusran",help="if y, make the clustering random files after the BAO blinding (needed for RSD blinding)",default='n')
parser.add_argument("--minr", help="minimum number for random files",default=0,type=int)#use 1 for abacus mocks
parser.add_argument("--maxr", help="maximum for random files, default is 1",default=1,type=int) #use 2 for abacus mocks
parser.add_argument("--dorecon",help="if y, run the recon needed for RSD blinding",default='n')
parser.add_argument("--rsdblind",help="if y, do the RSD blinding shift",default='n')

parser.add_argument("--fiducial_f",help="fiducial value for f",default=0.8)

#parser.add_argument("--fix_monopole",help="whether to choose f such that the amplitude of the monopole is fixed",default='y')


args = parser.parse_args()
print(args)

type = args.type
version = args.version
specrel = args.verspec

notqso = ''
if args.notqso == 'y':
    notqso = 'notqso'

print('blinding catalogs for tracer type '+type+notqso)


if type[:3] == 'BGS' or type == 'bright' or type == 'MWS_ANY':
    prog = 'BRIGHT'

else:
    prog = 'DARK'

progl = prog.lower()

mainp = main(args.type)
zmin = mainp.zmin
zmax = mainp.zmax
tsnrcol = mainp.tsnrcol  


#share basedir location '/global/cfs/cdirs/desi/survey/catalogs'
if 'mock' not in args.verspec:
    maindir = args.basedir_in +'/'+args.survey+'/LSS/'

    ldirspec = maindir+specrel+'/'

    dirin = ldirspec+'LSScats/'+version+'/'
    tsnrcut = mainp.tsnrcut
    dchi2 = mainp.dchi2
    randens = 2500.
    nzmd = 'data'
elif 'Y1/mock' in args.verspec: #e.g., use 'mocks/FirstGenMocks/AbacusSummit/Y1/mock1' to get the 1st mock with fiberassign
    dirin = args.basedir_in +'/'+args.survey+'/'+args.verspec+'/LSScats/'+version+'/'
    dchi2=None
    tsnrcut=0
    randens = 10460.
    nzmd = 'mock'

else:
    sys.exit('verspec '+args.verspec+' not supported')
    

dirout = args.basedir_out+'/LSScats/'+version+'/blinded/'


if not os.path.exists(dirout):
    os.makedirs(dirout)
    print('made '+dirout)


tp2z = {'LRG':0.8,'ELG':1.1,'QSO':1.6}
tp2bias = {'LRG':2.,'ELG':1.3,'QSO':2.3}
ztp = tp2z[args.type]
bias = tp2bias[args.type]

w0wa = np.loadtxt('/global/cfs/cdirs/desi/survey/catalogs/Y1/LSS/w0wa_initvalues_zeffcombined_1000realisations.txt')

if args.get_par_mode == 'random':
    if args.type != 'LRG':
        sys.exit('Only do LRG in random mode, read from LRG file for other tracers')
    ind = int(random()*1000)
    [w0_blind,wa_blind] = w0wa[ind]

if args.get_par_mode == 'from_file':
    hd = fitsio.read_header(dirout+ 'LRG_full.dat.fits',ext='LSS')
    ind = hd['FILEROW']
    [w0_blind,wa_blind] = w0wa[ind]

#choose f_shift to compensate shift in monopole amplitude
cosmo_fid = DESI()
cosmo_shift = cosmo_fid.clone(w0_fld=w0_blind, wa_fld=wa_blind)

DM_fid = cosmo_fid.comoving_angular_distance(ztp)
DH_fid = 1./cosmo_fid.hubble_function(ztp)

DM_shift = cosmo_shift.comoving_angular_distance(ztp)
DH_shift = 1./cosmo_shift.hubble_function(ztp)


vol_fac =  (DM_shift**2*DH_shift)/(DM_fid**2*DH_fid)

#a, b, c for quadratic formula
a = 0.2/bias**2.
b = 2/(3*bias)
c = 1-(1+0.2*(args.fiducial_f/bias)**2.+2/3*args.fiducial_f/bias)/vol_fac

f_shift = (-b+np.sqrt(b**2.-4.*a*c))/(2*a)

dfper = (f_shift-args.fiducial_f)/args.fiducial_f

maxfper = 0.1
if abs(dfper) > maxfper:
	dfper = maxfper*dfper/abs(dfper)
	f_shift = (1+dfper)*args.fiducial_f

fgrowth_blind = f_shift


#if args.reg_md == 'NS':
regl = ['_S','_N']
#if args.reg_md == 'GC':
gcl = ['_SGC','_NGC']


fb_in = dirin+type+notqso
fcr_in = fb_in+'_1_full.ran.fits'
fcd_in = fb_in+'_full.dat.fits'
nzf_in = dirin+type+notqso+'_full_nz.txt'
wo = 'y'
if os.path.isfile(nzf_in):
    wo = 'n'
if type[:3] == 'QSO':
    dz = 0.02
    zmin = 0.02
    zmax = 3.5
    P0 = 6000
else:
    dz = 0.01
    zmin = 0.01
    zmax = 1.6
    
if type[:3] == 'LRG':
    P0 = 10000
if type[:3] == 'ELG':
    P0 = 4000
if type[:3] == 'BGS':
    P0 = 7000

nz_in = common.mknz_full(fcd_in,fcr_in,type[:3],bs=dz,zmin=zmin,zmax=zmax,write=wo,randens=randens,md=nzmd)

fin = fitsio.read(fcd_in)
cols = list(fin.dtype.names)
if 'WEIGHT_FKP' not in cols:
    common.addFKPfull(fcd_in,nz_in,type[:3],bs=dz,zmin=zmin,zmax=zmax,P0=P0,md=nzmd)


if args.baoblind == 'y':
    data = Table(fitsio.read(dirin+type+notqso+'_full.dat.fits'))
    outf = dirout + type+notqso+'_full.dat.fits'
    blind.apply_zshift_DE(data,outf,w0=w0_blind,wa=wa_blind,zcol='Z_not4clus')

fb_out = dirout+type+notqso
fcd_out = fb_out+'_full.dat.fits'
nz_out = common.mknz_full(fcd_out,fcr_in,type[:3],bs=dz,zmin=zmin,zmax=zmax,randens=randens,md=nzmd,zcol='Z')

ratio_nz = nz_in/nz_out

fd = Table(fitsio.read(fcd_out))
cols = list(fd.dtype.names)
if 'WEIGHT_SYS' not in cols:
    fd['WEIGHT_SYS'] = np.ones(len(fd))
zl = fd['Z_not4clus']
zind = ((zl-zmin)/dz).astype(int)
gz = fd['ZWARN'] != 999999
gz &= zl > zmin
gz &= zl < zmax

wl = np.ones(len(fd))
wl[gz] = nz_in[zind[gz]]/nz_out[zind[gz]]
fd['WEIGHT_SYS'] *= wl
common.write_LSS(fd,fcd_out)

if args.type == 'LRG':
	hdul = fits.open(fcd_out,mode='update')
	hdul['LSS'].header['FILEROW'] = ind
	hdul.close()
	hdtest = fitsio.read_header(dirout+ 'LRG_full.dat.fits', ext='LSS')['FILEROW']
	if hdtest != ind:
		sys.exit('ERROR writing/reading row from blind file')
        



if args.mkclusdat == 'y':
    ct.mkclusdat(dirout+type+notqso,tp=type,dchi2=dchi2,tsnrcut=tsnrcut,zmin=zmin,zmax=zmax)


if args.mkclusran == 'y':
    rcols=['Z','WEIGHT','WEIGHT_SYS','WEIGHT_COMP','WEIGHT_ZFAIL']
    tsnrcol = 'TSNR2_ELG'
    if args.type[:3] == 'BGS':
        tsnrcol = 'TSNR2_BGS'
    for rannum in range(args.minr,args.maxr):
        ct.mkclusran(dirin+args.type+notqso+'_',dirout+args.type+notqso+'_',rannum,rcols=rcols,tsnrcut=tsnrcut,tsnrcol=tsnrcol)#,ntilecut=ntile,ccut=ccut)
        #for clustering, make rannum start from 0
        if 'Y1/mock' in args.verspec:
            for reg in regl:
                ranf = dirout+args.type+notqso+reg+'_'+str(rannum)+'_clustering.ran.fits'
                ranfm = dirout+args.type+notqso+reg+'_'+str(rannum-1)+'_clustering.ran.fits'
                os.system('mv '+ranf+' '+ranfm)

reg_md = args.reg_md

if args.split_GC == 'y':
    fb = dirout+args.type+notqso+'_'                
    ct.clusNStoGC(fb,args.maxr-args.minr)

sys.stdout.flush()

if args.dorecon == 'y':
    nran = args.maxr-args.minr
    if reg_md == 'NS':
        os.system('python recon.py --tracer '+args.type+' --prepare_blinding True --indir '+dirout+' --outdir '+dirout+' --nran '+str(nran))
    else:
        for gc in gcl:
            os.system('python recon.py --tracer '+args.type+' --prepare_blinding True --indir '+dirout+' --outdir '+dirout+' --nran '+str(nran)+' --region '+gc.strip('_'))

if args.rsdblind == 'y':
    if reg_md == 'NS':
        cl = regl
    if reg_md == 'GC':
        cl = gcl
    for reg in cl:
        fnd = dirout+type+notqso+reg+'_clustering.dat.fits'
        fndr = dirout+type+notqso+reg+'_clustering.MGrsd.dat.fits'
        data = Table(fitsio.read(fnd))
        data_real = Table(fitsio.read(fndr))

        out_file = fnd
        blind.apply_zshift_RSD(data,data_real,out_file,
                               fgrowth_fid=args.fiducial_f,
                               fgrowth_blind=fgrowth_blind)#,
                               #comments=f"f_blind: {fgrowth_blind}, w0_blind: {w0_blind}, wa_blind: {wa_blind}")

