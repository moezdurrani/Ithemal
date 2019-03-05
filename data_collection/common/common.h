#ifndef COMMON_COMMON
#define COMMON_COMMON

#include "dr_api.h"
#include <stdint.h>

//dr client data collection modes
#define SNOOP   1
#define SQLITE  2
#define RAW_SQL 3

//global character count constants
#define MAX_STRING_SIZE 128   //this is for generic strings
#define MAX_MODULE_SIZE 1024
#define MAX_CODE_SIZE 20480
#define MAX_QUERY_SIZE 20480

typedef struct{
  char compiler[MAX_STRING_SIZE];
  char flags[MAX_STRING_SIZE];
  uint32_t arch;
} config_t;

//code embedding structure
typedef struct{
  uint32_t control;
  char module[MAX_MODULE_SIZE];
  void * module_start; 
  char function[MAX_MODULE_SIZE];
  uint32_t code_type;
  char code[MAX_CODE_SIZE];
  int32_t code_size;
  uint32_t rel_addr; 
  uint32_t num_instr;
  uint32_t span;
} code_info_t;


typedef char query_t;

//code types array
#define CODE_INTEL 0
#define CODE_ATT   1
#define CODE_TOKEN 2


#endif
