#/bin/bash
clips=( "/scif/data/soilmask/*" )
echo ${clips}

found_files=0
echo "{\"CANOPYCOVER_FILE_LIST\": [" >> "/scif/data/soilmask/canopycover_fileslist.json"
sep=""
for entry in ${clips[@]}
do
  possible="${entry}/orthomosaic_mask.tif"
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
