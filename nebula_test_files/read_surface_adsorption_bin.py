import numpy as np
import os
import pickle
import sys
from statistics import median 
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib import rc
from matplotlib import cm
import matplotlib
import matplotlib.patches as mpatches
import matplotlib
import time
from struct import *

#This file is for reading surface voxels

#IDs
"""
0 - no ID
1 - surface voxels
2 - open site
3 - occupied site
4 - sources
5 - Tracked

"""


# IO parameters
date = "/August/29_8_2021/"
material = 'tungsten'
cross_section_type = '_SM_'
HPC_toggle = False #Set to true when running on HPC
direct_pathing = False #allow for direct input of file through command line
legacy_class_toggle = False # turn off old classifcation plots
desktop_toggle = True
distance_toggle = False
electron_time = 5.3 # 53 ns from smith paper wrong --> 5.3ns
time_segments = []

#parameter_summary = "1keV_1_1kpp_pitch_0_401_401_101_sb_1000_sd_34000_sh_96_detect_dome_vs_250_"
parameter_summary = "1keV_1_1000kpp_pitch_0_161_161_101_sb_1000_vs_250_sd_34000_sh_96_detect_dome_mirror_vs_250_"

#Input Paths
if HPC_toggle: #Adjustments for HPC environment
    #HPC path
    path_to_test_files = "/home/richarddejong/nebula_test_files/"
elif desktop_toggle:
    path_to_test_files = "C:/Users/Richard/source/repos/Nebula/nebula_test_files/"
else: 
    # Laptop path
    path_to_test_files= "C:/Users/richa/Documents/repos/nebula_test_files/"

#Direct Pathing via system argument (overwrites input_path above(does not change IO parameters))

input_path = path_to_test_files+"output"+date+parameter_summary+material+cross_section_type+"surface_MTL.bin"

#Arg Tests
print(sys.argv[0])
if direct_pathing:
    if(len(sys.argv) > 0):
	    input_path = str(sys.argv[-1])
    #Direct Pathing Translator (Just changes the \\ to / for interpretation)
    #input_path = input_path.replace("\\","/")

#Path Interpreter
path_list = (input_path.split('/')[-1]).split('.')
title =path_list[0]
title_list = title.split('_')
pillar_num = int(title_list[1])
pitch = float(int(title_list[4])/1000)
if title_list[2][0] == '0':
	electrons_per_pillar = int(title_list[2].split('-')[1].replace('kpp','')) #<1000 electrons
else:
	electrons_per_pillar = int(title_list[2].replace('kpp',''))*1000 #1000s of electrons
electron_num = pillar_num * electrons_per_pillar

output_path_folder = path_to_test_files+"figures"+date+title
#output_path_folder = "/mnt/c/Users/richa/Documents/repos/nebula_test_files/figures"+date+title #WSL
  
general_path = output_path_folder+"/"+title
fignum = 1

if not os.path.exists(output_path_folder):
    os.makedirs(output_path_folder)

# General path strings

cs_surf_hor_adsorb = general_path +"_cs_hor_surf_adsorb" # vertical cross section at a specific -X

#Text Loading
print("Loading file...")
tic =  time.perf_counter() 

with open(input_path, mode='rb') as file: # b is important -> binary
   fileContent = file.read()

#Binary Checks
unpack_flag = sys.byteorder
print('matplotlib: {}'.format(matplotlib.__version__))
#Binary Unpacking
print("System Byte Order: "+ unpack_flag)

#Binary Unpacking -HPC Changes made
lengrid = unpack("q", fileContent[:8])[0]
voxel_size = unpack("f", fileContent[8:12])[0]
dim = unpack("iii", fileContent[12:24])
counter = 24


mat_grid_in = unpack("h"*lengrid,fileContent[counter:counter+lengrid*2])
counter+=lengrid*2
surface_grid_in = unpack("h"*lengrid,fileContent[counter:counter+lengrid*2])
counter+=lengrid*2
lendist = unpack("i", fileContent[counter:counter+4])[0]
counter+=4
travel_dists = unpack("h"*lendist,fileContent[counter:counter+lendist*2])

#The stored bytes in order c++
""" 
	//Open and determine length of integer stream 
	std::ofstream output_bin_file(file_name, std::ios::binary);
	int64_t len = _mat_grid_slice.size();
	output_bin_file.write( (char*)&len, sizeof(len) );

	
	output_bin_file.write( (char*)&_voxel_size, sizeof(real) );
	output_bin_file.write( (char*)&_size_x, sizeof(int32_t) );
	output_bin_file.write( (char*)&_size_y, sizeof(int32_t) );
	output_bin_file.write( (char*)&_save_height, sizeof(int32_t) );

	//Vectors
	output_bin_file.write( (char*)&_mat_grid_slice_int16[0], len * sizeof(int16_t) );
	output_bin_file.write( (char*)&_surface_grid_slice_int16[0], len * sizeof(int16_t) );

	//New for Surface Tracking certain adsorbates
	output_bin_file.write( (char*)&len_distance, sizeof(int32_t) );
	output_bin_file.write( (char*)&_track_vec_slice_int16[0], len * sizeof(int16_t) );

    output_bin_file.close();
"""

toc = time.perf_counter()
time_segments.append(toc-tic)
print(f"Finished Loading in {toc - tic:0.4f} seconds")


#Start Timing Data Manipulation
print("Data Manipulation...")
tic = time.perf_counter()

#Grid Work
mat_grid = np.reshape(mat_grid_in, dim, order='F')
surface_grid = np.reshape(surface_grid_in, dim, order='F')
travel_dists = np.reshape(travel_dists,lendist)

#Fix Plots --switching x and y axes

mat_grid_t = mat_grid.transpose(1, 0, 2)
surface_grid_t = surface_grid.transpose(1, 0, 2)



# Finding Appropriate Plotting Restrictions-----------------------------------------

#Range Conversions to around 0 (keep pixels same size) (scales)
s_dims = [dim[0]/2,dim[1]/2]
s_dims_nm = [s_dims[0]*voxel_size,s_dims[1]*voxel_size]

#Fixed Width Ranges --------------------------------------------------------
f_range = 9.9#fixed range in nm
f_x = np.arange(start =-f_range,stop = f_range,step = voxel_size)
f_y = np.arange(start = -f_range,stop =f_range,step = voxel_size)
f_steps = len(f_x)/2
f_x_min = int(s_dims[0]-f_steps)
f_x_max = int(s_dims[0]+f_steps)
f_y_min = int(s_dims[1]-f_steps)
f_y_max = int(s_dims[1]+f_steps)
mat_grid_f = mat_grid_t[f_x_min:f_x_max,f_y_min:f_y_max,:]
surface_grid_f = surface_grid_t[f_x_min:f_x_max,f_y_min:f_y_max,:]

f_x = np.arange(start =-f_range,stop = f_range,step = voxel_size)
f_y = np.arange(start = -f_range,stop =f_range,step = voxel_size)

toc = time.perf_counter()
time_segments.append(toc-tic)
print(f"Finished Data Manipulation in {toc - tic:0.4f} seconds")

print("Creating Plots...")
tic = time.perf_counter()

#Data Analysis
hom_surface_grid_t = surface_grid_t.copy()
hom_surface_grid_t[hom_surface_grid_t == 5] = 3

resident_num = np.sum(hom_surface_grid_t == 3)
open_num = np.sum(hom_surface_grid_t == 2)
coverage = resident_num/(resident_num+open_num)

#Adsorption Plot
ul_plot = plt.figure(fignum)
ax = ul_plot.gca()
fignum+=1
plt.rcParams['font.size'] = 16
plt.xlabel("x (nm)")
plt.ylabel("y (nm)")
plt.imshow(hom_surface_grid_t[:, :, -1], extent=(-s_dims_nm[0], s_dims_nm[0], -s_dims_nm[1], s_dims_nm[1]))
time_tot = int(electron_time*electron_num/1000)
if time_tot == 0:
	time_tot = int(electron_time*electron_num)
	title_str =  str(time_tot)+"ns"
else:
	title_str =  str(time_tot)+"\u03bcs"




#plt.title(" Non Deposition 2D Surface Adsorption after " + title_str, pad = 8)

ul_plot.savefig(cs_surf_hor_adsorb, dpi = 200, bbox_inches="tight",extent=(-f_range, f_range, 0, dim[2] * voxel_size))

#Print Vals
print(str(np.round(coverage,4)*100) +"%")


toc = time.perf_counter()
time_segments.append(toc-tic)
print(f"Finished  Plots in {toc - tic:0.4f} seconds")

#Total Timing
segment_total = np.sum(np.asarray(time_segments))
print(f"Script Ran in {segment_total:0.4f} seconds")










