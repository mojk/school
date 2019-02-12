/* $Header: https://svn.ita.chalmers.se/repos/security/edu/course/computer_security/trunk/lab/login_linux/login_linux.c 585 2013-01-19 10:31:04Z pk@CHALMERS.SE $ */

/* gcc -Wall -g -o mylogin login.linux.c -lcrypt */

#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include <stdio_ext.h>
#include <string.h>
#include <signal.h>
#include <pwd.h>
#include <sys/types.h>
#include <crypt.h>
#include "pwent.h"
#include "time.h"

#define TRUE 1
#define FALSE 0
#define LENGTH 16

void sighandler() {
	printf("Caught signal! \n");
	/* we need to catch SIGINT(2), SIGQUIT(3), SIGTSTP(20) */
}

/* generating a random number withing the range of the argument limit */
int rand_lim(int limit) {
    int divisor = RAND_MAX/(limit+1);
    int return_value;

    do { 
        return_value = rand() / divisor;
    } while (return_value > limit);

    return return_value;
}

/* authentication for to many failed login attempts */
void random_captcha(char input[]) {
	char randomletters[53] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
	int random_int;
	for(int i = 0; i < 6; i++) {
		random_int = rand_lim(53);
		input[i] = randomletters[random_int];
	}
}

int main(int argc, char *argv[]) {
	mypwent *passwddata;
	
	char important[LENGTH] = "***IMPORTANT***";
	char user[LENGTH];
	char *arguments[] = {"/bin/sh", NULL};
	char prompt[] = "password: ";
	char *user_pass;
	char *hashed_pass;

	signal(2, sighandler);
	signal(3, sighandler);
	signal(20, sighandler);

	while (TRUE) {
		srand ( time(NULL) ); /* give our random generator a seed to avoid deterministic captcha */
		/* check what important variable contains - do not remove, part of buffer overflow test */
		printf("Value of variable 'important' before input of login name: %s\n",
				important);

		printf("login: ");
		fflush(NULL); /* Flush all  output buffers */
		__fpurge(stdin); /* Purge any data in stdin buffer */
		if (fgets(user,sizeof(user),stdin) == NULL) /* fgets() to avoid overflow attacks */
			exit(0);
		
		/* removing the '\n' character from the input when using fgets() */
		size_t ln = strlen(user) -1;
		if(*user && user[ln] == '\n')
			user[ln] = '\0';

		/* check to see if important variable is intact after input of login name - do not remove */
		printf("Value of variable 'important' after input of login name: %*.*s\n",
				LENGTH - 1, LENGTH - 1, important);

		user_pass = getpass(prompt);
		passwddata = mygetpwnam(user); 

		if (passwddata != NULL) {

			/* hashes the password from input using crypt() */
			hashed_pass = crypt(user_pass, passwddata->passwd_salt);
			
			if (!strcmp(hashed_pass, passwddata->passwd)) {

				printf(" You're in !\n");
				printf("Number of attempts: %d\n", passwddata->pwfailed);
				
				/* upon success, set the number of failed attempts to 0 and increase the pw-age */
				passwddata->pwfailed = 0;
				passwddata->pwage++;

				/* update the credentials */
				mysetpwent(user,passwddata);

				/* reminding the user to perhaps change their password when age>10 */
				if(passwddata->pwage > 10) {
					printf("Age of your password is >10! \n");
				}

				/* checking priviliges c
				 * if it fails, error is printed
				 */

				if((setuid(passwddata->uid)) == -1)
					printf("ERROR, not enough privileged");

				/* executing /bin/sh 
				 * if it fails, error is printed
				 */

				if((execve("/bin/sh",arguments,NULL)) == -1)
					printf("ERROR on executing");

			} else {

			/* if its not a match, the number of failed attempts will increase, and it will be printed */
			passwddata->pwfailed++;
			printf("Attempts %d\n",passwddata->pwfailed);
			
			/* update the credentials since an attempt has happend */
			mysetpwent(user,passwddata);
			
			/* we allow up to 3 continious tries until we let the user type in a captcha to prove that it is not a robot */
			if(passwddata->pwfailed > 3) {
				char input[LENGTH];
				char captcha[LENGTH];

				random_captcha(captcha);

				printf("Prove that you are not a robot, please type in the captcha..%s\n", captcha);

				/* user has to input captcha */
				fflush(NULL);
				__fpurge(stdin);
				if(fgets(input,LENGTH,stdin) != NULL) {

				/* removing \n */
				size_t s = strlen(input) -1;
				if(*input && input[s] == '\n')
				input[s] = '\0';

				/* comparing input and captcha */
				if(strcmp(input,captcha) != 0) {
					printf("Wrong captcha!\n" );
					break;
						} 
				printf("Correct captcha, you may now try again..\n");
					} 
				} 
			}
		}
		printf("Login Incorrect \n");
	}
	return 0;
}

