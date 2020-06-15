#/bin/bash
ORTHOMOSAIC_NAME="${1}_mask.tif"
echo "Orthomosaic name to look for: ${ORTHOMOSAIC_NAME}"
clips=( "/scif/data/soilmask/*" )
echo ${clips}

found_files=0
echo "{\"CANOPYCOVER_FILE_LIST\": [" >> "/scif/data/soilmask/canopycover_fileslist.json"
sep=""
for entry in ${clips[@]}
do
  possible="${entry}/${ORTHOMOSAIC_NAME}"
  echo "Checking possible ${possible}"
  if [ -f "${possible}" ]; then
    echo "${sep}{\"FILE\": \"${possible}\"," >> "/scif/data/soilmask/canopycover_fileslist.json"
    echo "\"DIR\": \"${entry}/\"}" >> "/scif/data/soilmask/canopycover_fileslist.json"
    sep=","
    ((found_files++))
  fi
done
echo "]}" >> "/scif/data/soilmask/canopycover_fileslist.json"

if [ "$found_files" -eq "0" ]; then
  rm "/scif/data/soilmask/canopycover_fileslist.json"
fi
