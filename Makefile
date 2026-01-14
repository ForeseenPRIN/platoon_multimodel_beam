# Disable all built-in implicit rules
.SUFFIXES:

# Disable all built-in variables
MAKEFLAGS += --no-builtin-rules
MAKEFLAGS += --no-builtin-variables

#MAESTRO ?= java -classpath ~/Scaricati/maestro-4.0.2-jar-with-dependencies.jar:/work/model/classpath org.intocps.maestro.Main
MAESTRO ?= java -classpath ~/Documenti/maestro-git/maestro/target/maestro-4.0.3-SNAPSHOT-jar-with-dependencies.jar:/work/model/classpath org.intocps.maestro.Main

MODELS = modelV2N modelV2V
BUILD_DIRS = $(addprefix build/,$(MODELS))
OUTPUTS = $(addsuffix /outputs.csv,$(BUILD_DIRS))

include options.env

.PHONY: all clean V2N test
.SECONDARY:
.NOTPARALLEL:

all: $(OUTPUTS)
V2N: build/modelV2N/outputs.csv
V2V: build/modelV2V/outputs.csv

clean:
	rm -rf build

$(BUILD_DIRS):
	mkdir -p $@

build/modelV2N/model.json: options.env | $(BUILD_DIRS)
	python generate_model.py -n $(N_CARS) -t V2N > $@

build/modelV2V/model.json: options.env | $(BUILD_DIRS)
	python generate_model.py -n $(N_CARS) -t V2V > $@

build/%/spec.mabl: build/%/model.json model.settings.json FMUs/BeamNG-FMI2.fmu 
	$(MAESTRO) import sg1 $< model.settings.json -fsp FMUs -output build/$*/

build/%/outputs.csv: build/%/spec.mabl
	python beam_start.py -n $(N_CARS)
	$(MAESTRO) interpret $< -tms 10 -output build/$*/

