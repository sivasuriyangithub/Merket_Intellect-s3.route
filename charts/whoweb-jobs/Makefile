CHART_REPO := http://jenkins-x-chartmuseum:8080
CURRENT=$(pwd)
TEAM := wkpython
IMAGE_NAME := xperweb
NAME := xperweb-jobs
OS := $(shell uname)
VERSION := $(shell cat ../../../VERSION)
REQUIREMENTS_PATH := ../../../charts/wkpython/requirements.yaml

debug:
	helm template --debug . | awk '/---/,0' - | kubeval - -v 1.10.4

build: clean
	rm -rf requirements.lock
	helm dependency build
	helm lint

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
	sed -i "" -e "s|repository:.*|repository: $(DOCKER_REGISTRY)/$(TEAM)/$(IMAGE_NAME)|" values.yaml
	sed -i "" -e "s/tag:.*/tag: $(VERSION)/" values.yaml
	gsed -i -e "/name: $(NAME)/!b;n;c\ \ \ \ version: $(VERSION)" $(REQUIREMENTS_PATH)
else ifeq ($(OS),Linux)
	sed -i -e "s/version:.*/version: $(VERSION)/" Chart.yaml
	sed -i -e "s|repository:.*|repository: $(DOCKER_REGISTRY)/$(TEAM)/$(IMAGE_NAME)|" values.yaml
	sed -i -e "s/tag:.*/tag: $(VERSION)/" values.yaml
	sed -i -e "/name: $(NAME)/!b;n;c\ \ \ \ version: $(VERSION)" $(REQUIREMENTS_PATH)
else
	echo "platfrom $(OS) not supported to release from"
	exit -1
endif