#/bin/bash
clips=( "/scif/data/soilmask/*" )
echo ${clips}

echo "{\"CANOPYCOVER_FILE_LIST\": [" >> "/scif/data/soilmask/canopycover_fileslist.json"
sep=""
for entry in ${clips[@]}
do
  possible="${entry}/odm_orthophoto_mask.tif"
  echo "Checking possible ${possible}"
  if [ -f "${possible}" ]; then
    echo "${sep}{\"FILE\": \"${possible}\"," >> "/scif/data/soilmask/canopycover_fileslist.json"
    echo "\"DIR\": \"${entry}/\"}" >> "/scif/data/soilmask/canopycover_fileslist.json"
    sep=","
  fi
done
echo "]}" >> "/scif/data/soilmask/canopycover_fileslist.json"
