#!/bin/bash

CURRENT_DIR=$(pwd)

if [[ ${CURRENT_DIR} == *bin ]];then
    CURRENT_DIR=$(dirname $CURRENT_DIR)
fi

PYTHON="python3.9"

VENV="${CURRENT_DIR}/venv"
LOG_DIR="${CURRENT_DIR}/logs"
LOG_FILE="${LOG_DIR}/setup.log"
CONFIG_FILE="${CURRENT_DIR}/config/app.setting.json"

PYTHONCACHE="${CURRENT_DIR}/__pycache__"

LOG() 
{
    echo "[`date`] - ${*}" | tee -a ${LOG_FILE}
}

SETUP_PLAYGROUND(){
    
    LOG "Seting up workplace ... Initiated"
    CLEAN_PLAYGROUND
    
    ${PYTHON} -m venv ${VENV}
    [ $? == 0 ] && LOG "Created environment ... Success" || LOG "Created environment ... Failed"

    source ${VENV}/bin/activate
    [ $VIRTUAL_ENV != "" ] && LOG " Inside Virtual environement ... $VIRTUAL_ENV" || exit 1

    pip install --upgrade pip
    pip install -r requirement.txt

    deactivate

    cp -p ${CONFIG_FILE} ${CONFIG_FILE}.orig

    LOG "Seting up workplace ... Completed"
    return

}

CLEAN_PLAYGROUND(){
    
    LOG "Cleaning workplace ... Initiated"
    [ "x$VIRTUAL_ENV" != "x" ] && deactivate
    [ -d ${VENV} ] && rm -rf ${VENV}
    [ -d ${LOG_DIR} ] && rm -rf ${LOG_DIR}/*
    [ -d ${PYTHONCACHE} ] && rm -rf ${PYTHONCACHE}
    LOG "Cleaning workplace ... Completed"

    return
}

HELP(){
cat <<EOF

  Usage : $0 Option

  Option :  setup -- Create playground
            clean -- Clean playground

EOF
}

MAIN(){

    case $1 in
	setup)
		SETUP_PLAYGROUND
		;;
	clean)
		CLEAN_PLAYGROUND
		;;
    help)
		HELP
		;;
	*)
		HELP
		;;
    esac
    
}

MAIN $*

