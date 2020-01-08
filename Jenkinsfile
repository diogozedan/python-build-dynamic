import groovy.json.JsonOutput
import groovy.json.JsonSlurper
import groovy.json.JsonSlurperClassic
import groovy.json.JsonBuilder

stageBuild()

def stageBuild() {
    node('EC2') {
        try {
            stage('Python build') {
                dir(env.BUILD_ID) {
                    git branch: "${env.BRANCH_NAME}", credentialsId: 'GITHUB_TOKEN', url: 'https://github.com/diogozedan/python-build-dynamic.git'
                    ENV_CONDA="python-dynamic"
                    
                    sh """
                        conda create -n ${ENV_CONDA} python=3.7 setuptools wheel -y
                        source ~/miniconda/etc/profile.d/conda.sh
                        conda activate ${ENV_CONDA}
                        python setup.py bdist_wheel
                    """
                    file = sh(script: "echo dist/*.whl", returnStdout: true).trim()
                    path = "${env.WORKSPACE}" + "/" + "${env.BUILD_ID}" + "/" + "${file}"
                }
            }
            // stageDBdeploy(path, "cluster")
            // stageDockerBuild('xxxx-xxx-dev')
            stageCheckEnvs('82350725222-dev')
        }
        catch (Exception e) {
            println("Build Failed. Exception ${e}")
            currentBuild.result = "FAILURE"
        }
        finally{
            deleteDir()
        }
    }
}

def stageDBdeploy(wheelName, clusterId){
    dbAddress = "https://databricks.cloud.databricks.com"
    requestHeader = "Content-Type: application/vnd.api+json"
    withCredentials([string(credentialsId: 'db-token', variable: 'DB_TOKEN')]) {
            
        stage('DataBricks Run') {
            try {
                String file = wheelName.substring(wheelName.lastIndexOf('/') + 1, wheelName.length())
                uploadFile=sh(
                    script: """
                    curl  \
                        -X POST \
                        -H \"Authorization: Bearer ${DB_TOKEN}\" \
                        -F contents=@${wheelName} -F path=/FileStore/jars/${file} \
                        -F overwrite=true \
                        ${dbAddress}/api/2.0/dbfs/put
                    """,
                    returnStdout: true
                )trim()
            }
            catch (Exception e) {
                println("Databricks Failed. Exception ${e}")
                currentBuild.result = "FAILURE"
            }
        }
    }
}

def stageDockerBuild(tfeWorkSpaceName){

    dockerRepo = "823992922333.dkr.ecr.us-east-1.amazonaws.com"
    dockerName = "python-build"
    dockerUrl = "${dockerRepo}/${dockerName}"
    dockerImageName = "${dockerUrl}:${env.BRANCH_NAME}-${BUILD_NUMBER}"
    dockerImageLatest = "${dockerUrl}:latest"
    build = 0
    stage('Container Delivery') {
        dir(env.BUILD_ID) {
            try {
                withCredentials([
                    file(credentialsId: 'credentials', variable: 'AWS_SHARED_CREDENTIALS_FILE')
                        ]) {

                            sh "mkdir -p docker aws"

                            writeFile file: 'aws/config', text: '''[default]
                            output = json
                            region = us-east-1
                            [profile xxx]
                            role_arn = arn:aws:iam::823992922333:role/Role
                            source_profile = default
                            region = us-east-1
                            '''
            
                            writeFile file: 'docker/config.json', text:'''
                            {
                                "credHelpers": {
                                    "823992922333.dkr.ecr.us-east-1.amazonaws.com": "ecr-login"
                                }
                            }
                            '''
                            // unstash 'pipeline-stash'

                            withEnv([
                                'AWS_SDK_LOAD_CONFIG=true',     // enable docker-credential-ecr-login take aws config
                                'AWS_CONFIG_FILE=aws/config',   // path to aws/config file
                                'AWS_PROFILE=xxx',          // assume role
                                'DOCKER_CONFIG=docker'          // path to docker config dir
                                ]) {
                                
                                sh """                          
                                docker build -t ${dockerImageName} .
                                docker push ${dockerImageName}
                                """ 
                                if (env.BRANCH_NAME == "master") {
                                    sh """
                                    docker tag ${dockerImageName} ${dockerImageLatest}
                                    docker push ${dockerImageLatest}
                                    docker rmi -f ${dockerImageLatest}
                                    """
                                }
                                sh "docker rmi -f ${dockerImageName} || true"
                            }
                            
                    }
                    build = 1
            }
            catch (Exception e) {
                println("Docker Failed. Expection: ${e}")
                currentBuild.result = "FAILURE"
                build = -1
            }                          
            if (build == 1) {
                stageTfeDeploy(tfeWorkSpaceName)
            }
        }
    }
}

def stageTfeDeploy(tfeWorkSpaceName){
    tfeAddress = "https://terraform.company.io"
    tfeOrgName = "OrgName"
    requestHeader = "Content-Type: application/vnd.api+json"

    withEnv([
        "TFE_WORKSPACE=${tfeWorkSpaceName}", 
        "TFE_ORG=${tfeOrgName}",
        "TF_LOG=1"
    ]) {   
        withCredentials([string(credentialsId: 'atlas_token', variable: 'ATLAS_TOKEN')]) {
            node('master'){    
                stage('TFE PushVars') {                        
                    // Update docker image name variable on tfe
                    if (env.BRANCH_NAME == "master") {
                        sh """
                        tfe pushvars \
                        -var docker_image=${dockerImageName} \
                        -tfe-address ${tfeAddress} \
                        -overwrite docker_image
                        """
                    } else {
                        sh """
                        tfe pushvars \
                        -var docker_image_user1=${dockerImageName} \
                        -var user1=${env.BRANCH_NAME} \
                        -tfe-address ${tfeAddress} \
                        -overwrite docker_image_user1 \
                        -overwrite user1
                        """
                    }
                }
                stage('TFE Run') {
                    getWsRequestEndPoint = "${tfeAddress}/api/v2/organizations/${tfeOrgName}/workspaces/${tfeWorkSpaceName}"
                    wsId=sh(
                        script: """
                        curl \
                            -s --header \
                            \"Authorization: Bearer ${ATLAS_TOKEN}\" \
                            --header \"${requestHeader}\" ${getWsRequestEndPoint} \
                            | jq -r .data.id
                        """,
                        returnStdout: true
                    ).trim()
                    if (wsId) {
                        // send tfe runs call
                        payloadFile = "tfe-run-payload.json"
                        writeFile file: payloadFile, text:"""
                        {
                            "data": {
                                "attributes": {
                                "is-destroy":false,
                                "message": "Jenkins Trigger"
                                },
                                "type":"runs",
                                "relationships": {
                                    "workspace": {
                                        "data": {
                                        "type": "workspaces",
                                        "id": "${wsId}"
                                        }
                                    }
                                }
                            }
                        }
                        """
                    } else {
                        error "ERROR: check tfe run API request"
                    }
                    runId=sh(
                        script: """
                        curl \
                            -s \
                            --header \"Authorization: Bearer ${ATLAS_TOKEN}\" \
                            --header \"${requestHeader}\" \
                            --request POST \
                            --data @${payloadFile} \
                            ${tfeAddress}/api/v2/runs | jq -r .data.id
                        """,
                        returnStdout: true
                    ).trim()
                }
            }
        }
    }
}

def stageCheckEnvs(tfeWorkSpaceName){
    
    tfeAddress = "https://terraform.company.io"
    tfeOrgName = "Collaborative-Forecasting"
    requestHeader = "Content-Type: application/vnd.api+json"

    withEnv([
        "TFE_WORKSPACE=${tfeWorkSpaceName}", 
        "TFE_ORG=${tfeOrgName}",
        "TF_LOG=1"
    ]) {   
        withCredentials([string(credentialsId: 'atlas_token', variable: 'ATLAS_TOKEN')]) { 
            node('master'){ 
                stage('TFE Pullvars') {                        
                    sh(
                        script:"""
                        variable=\$(tfe pullvars \
                        -tfe-address ${tfeAddress} \
                        -var user-images)
                        userimage="\${variable:15:\${#variable}-16}"
                        jq -n \$userimage > result
                        """,
                        returnStdout: true).trim()
                    //result = readJSON file:'result'
                    userimages = readFile('result').trim()
                    result = parseJsonText(userimages)
                    def found = false;
                    result.each{
                        key, value -> if (key == env.BRANCH_NAME) {
                        echo "key found"
                        found = true;
                        }
                    }
                    if (found == false) {
                        dockerImage = "823992922333.dkr.ecr.us-east-1.amazonaws.com/repo/image:latest"
                        result.put(env.BRANCH_NAME,dockerImage)
                        def newImages = JsonOutput.toJson(result).toString()
                        def newImagesJson = JsonOutput.prettyPrint(newImages).toString()
                        def escapedJson = JsonOutput.toJson(newImages)
                        

                        getWsRequestEndPoint = "${tfeAddress}/api/v2/organizations/${tfeOrgName}/workspaces/${tfeWorkSpaceName}"
                        varId = "var-f6dbdhdfh"
                        wsId=sh(
                            script: """
                            curl \
                                -s --header \
                                \"Authorization: Bearer ${ATLAS_TOKEN}\" \
                                --header \"${requestHeader}\" ${getWsRequestEndPoint} \
                                | jq -r .data.id
                            """,
                            returnStdout: true
                        ).trim()
                        if (wsId) {
                            // send tfe runs call
                            payloadFile = "tfe-run-payload.json"
                            writeFile file: payloadFile, text:"""
                            {
                                "data": {
                                    "id": "${varId}",
                                    "attributes": {
                                        "key":"user-images",
                                        "value": ${escapedJson},
                                        "category":"terraform",
                                        "hcl": false,
                                        "sensitive": false
                                    },
                                    "type":"vars"
                                }
                            }
                            """
                        } else {
                            error "ERROR: check tfe run API request"
                        }
                        runId=sh(
                            script: """
                            curl \
                                -s \
                                --header \"Authorization: Bearer ${ATLAS_TOKEN}\" \
                                --header \"${requestHeader}\" \
                                --request PATCH \
                                --data @${payloadFile} \
                                ${tfeAddress}/api/v2/vars/${varId}
                            """,
                            returnStdout: true
                        ).trim()
                        sh "echo ${runId}"
                        
                    } else {
                        sh "echo Existing branch"
                    }

            }
        }
    }
}

@NonCPS
def parseJsonText(String json) {
  def object = new JsonSlurper().parseText(json)
  if(object instanceof groovy.json.internal.LazyMap) {
      return new HashMap<>(object)
  }
  return object
}

@NonCPS
def getData(String json) {
   def jsonSlurper = new JsonSlurper() 
   def resultJson = jsonSlurper.parseText(json)
   return resultJson
}

@NonCPS
def jsonParse(def json) {
    new groovy.json.JsonSlurperClassic().parseText(json)
}

@NonCPS
def jsonBuilder(def json) {
    def builder = new JsonBuilder()
    def jsonbuilder = builder(json)
    def jsonString = jsonbuilder.toString()
    return jsonString
}

