FROM python-lambda-pokemon:initial

COPY requirementsLambda.txt ${LAMBDA_TASK_ROOT}
COPY DatabaseImageMatchingLibrary ${LAMBDA_TASK_ROOT}

COPY lambda_function.py ${LAMBDA_TASK_ROOT}
COPY testMatching.py ${LAMBDA_TASK_ROOT}
COPY settings.json ${LAMBDA_TASK_ROOT}

#COPY SIFT.npz ${LAMBDA_TASK_ROOT}/matchingScript/
#COPY Database_Descriptors.npy ${LAMBDA_TASK_ROOT}/matchingScript/
#COPY Database_Dict.json ${LAMBDA_TASK_ROOT}/matchingScript/

CMD [ "lambda_function.lambda_handler" ]
