"""
# Generate Housing Unit File

Functions to obtain and clean data required for the version 2 Housing Unit Inventory. 
The workflow  replicates the original version 1 (alpha version)
of Housing Unit Inventory workflow in Python using Census API. 

The workflow also expands the Housing Unit Inventory to include
household income based on family and non-family income distributions 
by race and ethnicity.

For version 1 of the housing unit inventory 
process and example applications see:

Rosenheim, Nathanael (2021) “Detailed Household and Housing Unit Characteristics: 
Data and Replication Code.” DesignSafe-CI. 
https://doi.org/10.17603/ds2-jwf6-s535.

The 2010 Census Data provides detailed household and housing unit, 
level characteristics at the census block level. 

The 2012 5-year American Community Survey provides detailed 
household level characteristics at the census tract level.

## Description of Program
- program:    ncoda_1av1_run_HUI_v2_workflow
- task:       Obtain and clean data for Housing Unit Inventory.
- See github commits for description of program updates
- Current Version:    2022-03-31 - preparing for publication
- project:    Interdependent Networked Community Resilience Modeling Environment 
        (IN-CORE), Subtask 5.2 - Social Institutions
- funding:	  NIST Financial Assistance Award Numbers: 70NANB15H044 and 70NANB20H008 
- author:     Nathanael Rosenheim

- Suggested Citation:
Rosenheim, Nathanael. (2022). "Detailed Household and Housing Unit 
Characteristics: Data and Replication Code." [Version 2] 
DesignSafe-CI. https://doi.org/10.17603/ds2-jwf6-s535

"""
import numpy as np
import pandas as pd
import os # For saving output to path
import urllib
import sys

# Functions from IN-CORE
from pyincore import IncoreClient, DataService

# open, read, and execute python program with reusable commands
from pyncoda.CommunitySourceData.api_census_gov.acg_05a_hui_functions \
    import hui_workflow_functions
from pyncoda.ncoda_00b_directory_design import directory_design
from pyncoda.ncoda_06c_Codebook import *
from pyncoda.ncoda_04a_Figures import *

from pyncoda.CommunitySourceData.api_census_gov.acg_00e_incore_huiv2 \
    import incore_v2_DataStructure

class generate_hui_functions():
    """
    Function runs full process for generating the housing unit inventories
    Process runs for multiple counties.

    Outputs CSV files and Codebooks
    """

    def __init__(self,
            communities,
            seed: int = 9876,
            version: str = '2.0.0',
            version_text: str = 'v2-0-0',
            basevintage: str = 2010,
            outputfolder: str ="",
            outputfolders = {},
            savefiles: bool = True):

        self.communities = communities
        self.seed = seed
        self.version = version
        self.version_text = version_text
        self.basevintage = basevintage
        self.outputfolder = outputfolder
        self.outputfolders = outputfolders
        self.savefiles = savefiles


        # Save Outputfolder - due to long folder name paths output saved to folder with shorter name
        # files from this program will be saved with the program name - 
        # this helps to follow the overall workflow
        # Make directory to save output
        if not os.path.exists(self.outputfolder):
            os.mkdir(self.outputfolder)


    def loginto_incore_dataservice(self):
        """
        code for logging into IN-CORE
        
        Set up pyincore and read in data
        IN-CORE is an open source python package that can be used to model the resilience of a community. To download IN-CORE, see:

        https://incore.ncsa.illinois.edu/

        Registration is free.

        """

        client = IncoreClient()
        # IN-CORE caches files on the local machine, it might be necessary to clear the memory
        #client.clear_cache() 

        # create data_service object for loading files
        data_service = DataService(client)

        return data_service

    def check_file_on_incore(self, title):
        """
        Check if HUI data is on IN-CORE
        """

        data_service = self.loginto_incore_dataservice()
        # Search Data Services for dataset

        url = urllib.parse.urljoin(data_service.base_url, "search")
        search_title = {"text": title}
        matched_datasets = data_service.client.get(url, params=search_title)

        return matched_datasets

    def return_dataservice_id(self, title, output_filename):
        
        # Check if file exists on IN-CORE
        matched_datasets = self.check_file_on_incore(title)
        match_count = len(matched_datasets.json())
        print(f'Number of datasets matching {title}: {match_count}')
    
        if match_count == 1:
            for dataset in matched_datasets.json():
                incore_filename = dataset['fileDescriptors'][0]['filename']
                if (dataset['title'] == title) and (incore_filename == output_filename+'.csv'):
                    print(f'Dataset {title} already exists in IN-CORE')
                    print(f'Dataset already exists in IN-CORE with filename {incore_filename}')
                    dataset_id = dataset['id']
                    print("Use dataset_id:",dataset_id)
                    
                    # Exit function and return dataset_id
                    return dataset_id
                else:
                    print(f'Dataset {title} ')
                    print(f'with matching filename {incore_filename} does not exist in IN-CORE')

                    return None
        elif match_count == 0:
            print(f'Dataset {title} does not exist in IN-CORE')

            return None
        else:
            print("There are multiple datasets matching the title. Please select one.")
            for i, dataset in enumerate(matched_datasets):
                print(i,matched_datasets[i]['dataset']['id'])
            dataset_id = matched_datasets[int(input("Enter dataset number: "))]['dataset']["id"]
            print("Use dataset_id:",dataset_id)
            return dataset_id

    def generate_hui_v2_for_incore(self):
        """
        Generate HUI data for IN-CORE
        """

        for community in self.communities.keys():
            # Create empty container to store outputs for in-core
            # Will use these to combine multiple counties
            hui_incore_county_df = {}
            title = "Housing Unit Inventory v2.0.0 data for "+self.communities[community]['community_name']
            print("Generating",title)
            output_filename = f'hui_{self.version_text}_{community}_{self.basevintage}_rs{self.seed}'
            county_list = ''

            # Check if file exists on IN-CORE
            dataset_id = self.return_dataservice_id(title, output_filename)

            # if dataset_id is not None, return id
            if dataset_id is not None:
                print("Dataset already exists on IN-CORE, use dataset_id:",dataset_id)
                return dataset_id
    
            # Workflow for generating HUI data for IN-CORE
            for county in self.communities[community]['counties'].keys():
                state_county = self.communities[community]['counties'][county]['FIPS Code']
                state_county_name  = self.communities[community]['counties'][county]['Name']
                print(state_county_name,': county FIPS Code',state_county)
                county_list = county_list + state_county_name+': county FIPS Code '+state_county

                # create output folders for hui data generation
                outputfolders = directory_design(state_county_name = state_county_name,
                                                    outputfolder = self.outputfolder)
                                                    
                generate_df = hui_workflow_functions(
                    state_county = state_county,
                    state_county_name= state_county_name,
                    seed = self.seed,
                    version = self.version,
                    version_text = self.version_text,
                    basevintage = self.basevintage,
                    outputfolder = self.outputfolder,
                    outputfolders = outputfolders)

                # Generate base housing unit inventory
                base_hui_df = generate_df.run_hui_workflow()
                hui_df = generate_df.final_polish_hui(base_hui_df['primary'])

                # Save version for IN-CORE in v2 format
                hui_incore_county_df[state_county] = \
                    generate_df.save_incore_version2(hui_df)

            # combine multiple counties
            hui_incore_df = pd.concat(hui_incore_county_df.values(), 
                                            ignore_index=True, axis=0)

            # Remove .0 from data
            hui_incore_df_fixed = hui_incore_df.applymap(lambda cell: int(cell) if str(cell).endswith('.0') else cell)

            #Save results for community name
            csv_filepath = outputfolders['top']+"/"+output_filename+'.csv'
            savefile = sys.path[0]+"/"+csv_filepath
            hui_incore_df_fixed.to_csv(savefile, index=False)

            # Save second set of files in common directory
            common_directory = outputfolders['top']+"/../../"+output_filename
            hui_incore_df_fixed.to_csv(common_directory+'.csv', index=False)
            
            # Generate figures for explore data
            figures_list = []
            for by_var in ["race","hispan","family"]:
                income_by_var_figure = income_distribution(input_df = hui_incore_df,
                                variable = "randincome",
                                by_variable = by_var,
                                datastructure = incore_v2_DataStructure,
                                communities= self.communities,
                                community = community,
                                year = self.basevintage,
                                outputfolders = outputfolders)
                filename = income_by_var_figure+".png"
                figures_list.append(filename)

            # Paths for codebook text
            CommunitySourceData_filepath = "pyncoda\\CommunitySourceData\\api_census_gov"
            keyterms_filepath = CommunitySourceData_filepath+ \
                    '\\'+"acg_00a_keyterms.md"

            projectoverview_filepath = 'pyncoda\\'+ "ncoda_00a_projectoverview.md"

            # Create PDF Codebook
            pdfcodebook = codebook(input_df = hui_incore_df_fixed,
                    header_title = 'Housing Unit Inventory',
                    datastructure = incore_v2_DataStructure,
                    projectoverview = projectoverview_filepath,
                    keyterms = keyterms_filepath,
                    communities = self.communities,
                    community = community,
                    year = self.basevintage,
                    output_filename = output_filename,
                    outputfolders = outputfolders,
                    figures = figures_list,
                    image_path = 'IN-CORE_HRRC_Banner.png')
            pdfcodebook.create_codebook()

            # Upload CSV file to IN-CORE and save dataset_id
            # note you have to put the correct dataType as well as format
            hui_description =  '\n'.join(["2010 Housing Unit Inventory v2.0.0 with required IN-CORE columns. " 
                   "Compatible with pyincore v1.4. " 
                   "Unit of observation is housing unit. " 
                   "Detailed characteristics include number of persons, race, ethnicity, "
                   "vacancy type, group quarters type, and household income. " 
                   "For more details on this data file refer to " 
                   "Rosenheim, Nathanael (2021) 'Detailed Household and " 
                   "Housing Unit Characteristics: Data and Replication Code.' "
                   "DesignSafe-CI. https://doi.org/10.17603/ds2-jwf6-s535. "
                   "For more details on the replication code, refer to " 
                   "Rosenheim, Nathanael. (2022). npr99/intersect-community-data. Zenodo. " 
                   "https://doi.org/10.5281/zenodo.6476122. "
                   "File includes data for "+county_list])

            dataset_metadata = {
                "title":title,
                "description": hui_description,
                "dataType": "incore:housingUnitInventory",
                "format": "table"
                }

            data_service = self.loginto_incore_dataservice()
            created_dataset = data_service.create_dataset(properties = dataset_metadata)
            dataset_id = created_dataset['id']
            print('dataset is created with id ' + dataset_id)

            ## Attach files to the dataset created
            files = [csv_filepath]
            full_dataset = data_service.add_files_to_dataset(dataset_id, files)

            print('The file(s): '+ output_filename +" have been uploaded to IN-CORE")
            print("Dataset now on IN-CORE, use dataset_id:",dataset_id)
            print("Dataset is only in personal account, contact IN-CORE to make public")

        return dataset_id

