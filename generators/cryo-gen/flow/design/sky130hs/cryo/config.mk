export DESIGN_NICKNAME = cryo
export DESIGN_NAME = cryoInst

export PLATFORM    = sky130hs
#export VERILOG_FILES = $(sort $(wildcard ./designs/src/$(DESIGN_NICKNAME)/*.v))

export VERILOG_FILES 		= $(sort $(wildcard ./design/src/$(DESIGN_NICKNAME)/*.v)) 

export SDC_FILE    		= ./design/$(PLATFORM)/$(DESIGN_NICKNAME)/constraint.sdc

export DIE_AREA   	 	= 0 0 96 34 
export CORE_AREA   		= 2.32 2.32 93.68 31.68

export PDN_CFG 			= ../blocks/$(PLATFORM)/pdn.cfg

# export ADDITIONAL_LEFS  	= ../blocks/$(PLATFORM)/lef/HEADER.lef \
#                         	  ../blocks/$(PLATFORM)/lef/SLC.lef

# export ADDITIONAL_GDS_FILES 	= ../blocks/$(PLATFORM)/gds/HEADER.gds \
# 			      	  ../blocks/$(PLATFORM)/gds/SLC.gds

# export DOMAIN_INSTS_LIST 	= ../blocks/$(PLATFORM)/$(DESIGN_NAME)_domain_insts.txt

# export CUSTOM_CONNECTION 	= ../blocks/$(PLATFORM)/$(DESIGN_NAME)_custom_net.txt

#export ADD_NDR_RULE		= 1
#export NDR_RULE_NETS 		= r_VIN
#export NDR_RULE 		= NDR_2W_2S
