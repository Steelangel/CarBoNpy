# -*- coding: utf-8 -*-
'''
CarBon_1.0.1.py - Kinetic Molecular Chemistry Code for Supernova Ejecta

Copyright (c) 2012-2016 Ethan Deneault 
This file is part of CarBoN

''' 

from scipy.integrate import odeint
from sys import exit

import datainput
import models
import numpy as np

file_format, species_file, reactions_file, output_file, model_type, density, Tinit, start_time, end_time, outfile = datainput.settings()
initial_abundances = datainput.abundances()
print(initial_abundances)
##############################################################################
# The Following code reads the data files in KIDA format and BASIC format 
##############################################################################
kida_reac = datainput.KIDA_reac(reactions_file)
kida_spec = datainput.KIDA_spec(species_file)
kida_reac = datainput.KIDA_reac_com_readable(kida_reac,kida_spec)

"""
This list contains the monoatomic molecules that result from the use of 'M' 
in the KIDA files
C, O, Si
"""

monoatomic_list = [0, 1, 21]



count=len(list(kida_reac.index))




##############################################################################
# The following are functions that determine the reaction coefficients 
# for each reaction.
##############################################################################

def arrhenius(a,b,c,T,formula):
    a *= 3.154e+7     # Convert units to year**-1

    # Formula choosing subroutine (from KIDA data set)
    if formula==1:                    #Cosmic Ray Ionization
        zeta = 2.0e-17                    #H2 ionization rate
        k = a * zeta

    elif formula==2:                  #Photodissociation (Draine)
        Av = 1                        #Av = visual extinction
        k = a * np.exp(-c * Av)

    elif formula==3:                  #Modified Arrhenius
        k = a * (T/300) ** b * np.exp(-c / T)

    elif formula==4:                  #ionpol 1   
        k = a * b * (0.62+0.4767 * c * np.sqrt(300. / T))

    elif formula==5:                  #ionpol 2
        k = a * b * (1 + 0.0967 * c * np.sqrt(300. / T) \
        + (300 * c ** 2) / (10.526 * T))
    else:
        exit("Unknown Formula!")

    return k

##############################################################################
# The following code builds the chemical network
##############################################################################

def chemnet(y,t):
    f=np.zeros([len(kida_spec.index)])
 
# Model Selection for T(t) and n(t)
    if model_type=='CD':
        T,Ndens=models.cherchneffT(y,t,kida_spec['species_#'].to_dict(),
                                   kida_spec['#_of_atoms'].to_dict(),
                                   dens=Ndensinit,
                                   T0=Tinit)
    elif model_type=='Yu':
        T,Ndens=models.YuT(t,dens=Ndensinit,T0=Tinit)
    else:
        exit("No Model Loaded, Exiting Now.")

    for num in range(count):
        
        in1=int(kida_reac.loc[num]['Input1_id'])
        in2=int(kida_reac.loc[num]['Input2_id'])
        out1=int(kida_reac.loc[num]['Output1_id'])
        out2=int(kida_reac.loc[num]['Output2_id'])
        out3=int(kida_reac.loc[num]['Output3_id'])
        alpha=kida_reac.loc[num]['alpha']
        beta=kida_reac.loc[num]['beta']
        gamma=kida_reac.loc[num]['gamma']
        fo=kida_reac.loc[num]['Formula']

        if num==0:
            print('Still going! t={0}, Temp={1}'.format(t,T))

        if (in2!=18 or in2!=19 or in2!=20) and in2!=98:
            f[in1] -= Ndens * arrhenius(alpha,beta,gamma,T,fo) \
                      * y[in1] * y[in2]
            f[in2] -= Ndens * arrhenius(alpha,beta,gamma,T,fo) \
                      * y[in1] * y[in2]
            f[out1] += Ndens * arrhenius(alpha,beta,gamma,T,fo) \
                       * y[in1] * y[in2]          
            f[out2] += Ndens * arrhenius(alpha,beta,gamma,T,fo) \
                       * y[in1] * y[in2]           
            if out3!=18 or in2==19 or in2==20:
                f[out3] += Ndens * arrhenius(alpha,beta,gamma,T,fo) \
                           * y[in1] * y[in2]
        elif in2==98:
            f[in1] -= Ndens * arrhenius(alpha,beta,gamma,T,fo) \
                      * y[in1] * (monoatomic_list[0]\
                         + monoatomic_list[1] \
                      + monoatomic_list[2])
            f[out1] += Ndens * arrhenius(alpha,beta,gamma,T,fo) \
                       * y[in1] * (monoatomic_list[0] + monoatomic_list[1] \
                       + monoatomic_list[2]) 
            f[out2] += Ndens * arrhenius(alpha,beta,gamma,T,fo) * y[in1] \
                       * (monoatomic_list[0] + monoatomic_list[1] \
                       + monoatomic_list[2])
            f[out3] += Ndens * arrhenius(alpha,beta,gamma,T,fo) * y[in1] \
                       * (monoatomic_list[0] + monoatomic_list[1] \
                       + monoatomic_list[2])
        elif in2==18 or in2==19 or in2==20:
            f[in1] -= arrhenius(alpha, beta, gamma, T, fo) * y[in1]
            f[out1] += arrhenius(alpha, beta, gamma, T, fo) * y[in1] 
            f[out2] += arrhenius(alpha, beta, gamma, T, fo) * y[in1]
            f[out3] += arrhenius(alpha, beta, gamma, T, fo) * y[in1]
    print(f)        
    return f

##############################################################################
# The following code sets the time steps
##############################################################################

time = np.linspace(start_time/365.25,end_time/365.25,1000000)

##############################################################################
# The following are the initial values
##############################################################################

yinit = np.zeros([len(kida_spec.index)]) 
                           
for species,abund in initial_abundances.items():
    yinit[int(species)] = abund
    print(species,abund,yinit)

         
Ndensinit = density #np.sum(yinit)*density

#print('Ndensinit = {}'.format(Ndensinit))

#exit()

##############################################################################
# The following initializes LSODA
##############################################################################

y = odeint(chemnet, yinit, time, 
           mxstep=5000000, rtol=1e-13, atol=1e-13)

##############################################################################
# The following plots the final abundances
##############################################################################

abundance=[]

for i in range(len(kida_spec.index)):
    abundance.append(y[-1,i])

print(abundance)

##############################################################################
# The following writes to a data file
##############################################################################

np.savez(output_file,time=time,speciesidx=kida_spec['species_#'].to_dict(), y = y,
         abundance=abundance,speciesmass=kida_spec['#_of_atoms'].to_dict())