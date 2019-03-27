#include <string.h>
#include <stdio.h>
#include "sql_dump_v2.h"

// dropping support for sqlite and solely focused on MYSQL syntax
// reason why we do not directly insert into the database is because
// if you use DR to collect executed BBs, rather than as a decoding library
// it will not work since MYSQL library requires pthread support.

int insert_architecture(query_t * query, config_t * config){
  
  int pos = 0;
  pos += sprintf(query, "INSERT INTO cpu_desc (name, vendor) VALUES ('%s', '%s');\n", config->name, config->vendor);
  pos += sprintf(query + pos, "SET @arch_id = (SELECT arch_id from cpu_desc WHERE name = '%s' AND vendor ='%s');\n", config->name, config->vendor);
  return pos;

}

int insert_config(query_t * query, config_t * config){
  int pos = 0;
  pos += sprintf(query, "INSERT INTO config (compiler, flags, arch) VALUES ('%s','%s', @arch_id);\n", config->compiler, config->flags);
  pos += sprintf(query + pos,"SET @config_id = (SELECT config_id FROM config WHERE compiler = '%s' AND flags = '%s' AND arch = @arch_id);\n", config->compiler, config->flags);
  return pos;
}

int insert_code(query_t * query, code_info_t * cinfo){

  int pos = 0;
  pos += sprintf(query, "INSERT INTO code (code_raw) VALUES (0x");
  
  int i = 0;
  for(i = 0; i < cinfo->code_size; i++){
    pos += sprintf(query + pos, "%x", cinfo->code[i]);
  } 

  pos += sprintf(query + pos, ");\n");
  return pos;

}


int insert_code_metadata(query_t * query, code_info_t * cinfo){

  int pos;
  pos = sprintf(query, "INSERT INTO code_metadata (config_id, code_id, module, rel_addr) VALUES (@config_id, LAST_INSERT_ID(), '%s',%d);\n",cinfo->module, cinfo->rel_addr);
  if(strlen(cinfo->function) > 0){
    pos += sprintf(query + pos, "UPDATE code_metadata SET function='%s' WHERE metadata_id=LAST_INSERT_ID();\n", cinfo->function); 
  }
  return pos;

}
