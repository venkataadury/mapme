#!/bin/bash

micromamba create -f env.yml -n mapme_env
if test $? -ne 0
then
	echo "Creating env failed. Check that you have micromamba installed"
	echo "Find micromamba here: https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html"
	exit 2
fi
eval "$(micromamba shell hook --shell bash)"
micromamba activate mapme_env
pip3 install pygame pygame_widgets
