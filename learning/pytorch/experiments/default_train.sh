#!/usr/bin/env bash

if [ "$#" -lt 1 ]; then
    echo "Requires a name parameter"
    exit 1
fi

NAME=$1; shift

bash "${ITHEMAL_HOME}/learning/pytorch/experiments/train.sh" "${NAME}" --trainers 4 --threads 4 "${@}"
