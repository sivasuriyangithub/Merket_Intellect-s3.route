CHART_REPO := http://jenkins-x-chartmuseum:8080
CURRENT=$(pwd)
TEAM := wkpython
NAME := whoweb
OS := $(shell uname)
VERSION := $(shell cat ../../../buildutils/vars/VERSION)
REQUIREMENTS_PATH := ../../../charts/wkpython/requirements.yaml


build: clean
	rm -rf requirements.lock
	helm dependency build
	helm lint

debug:
	helm template --debug . | awk '/---/,0' - | kubeval - -v 1.10.4

install: clean build
	helm install . --name ${NAME}

upgrade: clean build
	helm upgrade ${NAME} .

delete:
	helm delete --purge ${NAME}

clean:
	rm -rf charts
	rm -rf ${NAME}*.tgz

release: clean
	helm init --client-only
	helm repo add chartmuseum $(CHART_REPO)
	helm dependency build
	helm lint
	helm package .
	curl --fail -u $(CHARTMUSEUM_CREDS_USR):$(CHARTMUSEUM_CREDS_PSW) --data-binary "@$(NAME)-$(shell sed -n 's/^version: //p' Chart.yaml).tgz" $(CHART_REPO)/api/charts
	rm -rf ${NAME}*.tgz%

chart:
ifeq ($(OS),Darwin)
	sed -i "" -e "s/version:.*/version: $(VERSION)/" Chart.yaml
	sed -i "" -e "s|repository:.*|repository: gcr.io/wkinfra-171623/wkpython/$(NAME)|" values.yaml
	sed -i "" -e "s/tag:.*/tag: $(VERSION)/" values.yaml
	gsed -i -e "/name: $(NAME)/!b;n;c\ \ \ \ version: $(VERSION)" $(REQUIREMENTS_PATH)
else ifeq ($(OS),Linux)
	sed -i -e "s/version:.*/version: $(VERSION)/" Chart.yaml
	sed -i -e "s|repository:.*|repository: gcr.io/wkinfra-171623/wkpython/$(NAME)|" values.yaml
	sed -i -e "s/tag:.*/tag: $(VERSION)/" values.yaml
	sed -i -e "/name: $(NAME)/!b;n;c\ \ \ \ version: $(VERSION)" $(REQUIREMENTS_PATH)
else
	echo "platfrom $(OS) not supported to release from"
	exit -1
endif
