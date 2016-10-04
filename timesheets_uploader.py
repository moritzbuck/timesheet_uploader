

from redmine import Redmine
import datetime
import shutil
import sys, getopt
import getpass


help_message = """
timesheets_uploader.py -s <time_sheet_file> -k <key_table> -u <user_name>

time_sheet_file is a file with the time entries
key_table is a table linking project/issues with simple keys

user_name is your redmine username, if not added will be prompted for
"""

def main(argv):
    time_sheet_file = "time_sheet.tsv"
    pseudo_table = "pseudo_table.tsv"
    user = None
    try:
        opts, args = getopt.getopt(argv,"hs:k:u:")
    except getopt.GetoptError:
        print help_message
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print help_message
            sys.exit()
        elif opt == "-s":
            time_sheet_file = arg
        elif opt == "-k":
            pseudo_table = arg
        elif opt == "-u" :
            user = arg

    if not user:
        user = raw_input("Enter your redmine username: ")

    with open(time_sheet_file) as handle:
        temp = [ l[:-1].split("\t") for l in handle.readlines()]

    head = temp[0][1:]
    time_sheet = {l[0] : {f[0] : f[1] for f in zip(head,l[1:]) } for l in temp[1:]}

    with open(pseudo_table) as handle:
        temp = [ l[:-1].split("\t") for l in handle.readlines()]

    kk = temp[0][1:]
    keys = {l[0] : {f[0] : f[1] for f in zip(kk,l[1:]) } for l in temp[1:]}

    bils = Redmine('https://projects.bils.se/', username=user, password=getpass.getpass("type your redmine_password:"))
    activity_IDs = {a.name : a.id for a in bils.enumeration.filter(resource='time_entry_activities')}
    activities = {}

    for k, record in time_sheet.iteritems():
        if record['uploaded'] == 'FALSE':
            try :
                redmine_info = keys[record['pseudo']]
                activity = [keys[record['pseudo']]['activity'], record['activity']]
                activity = [a for a in activity if a != "None"]
                assert len(activity) == 1
                activity = activity[0]
                te =  bils.time_entry.new()
                type = redmine_info['type']

                if type == "issue":
                    te.issue_id = redmine_info['ID']
                else:
                    te.project_id = redmine_info['ID']

                te.hours = record['hours']

                d = str(record['year']) + "-W" + str(int(record['week']))
                r = datetime.datetime.strptime(d + '-3', "%Y-W%W-%w").date()

                te.spent_on = r
                te.activity_id = activity_IDs[activity]
                te.comments = record['notes']

                activities[k] = te

            except KeyError as ke:
                if str(ke) == "pseudo":
                    print record['pseudo'],"is not in your list of pseudos, please correct this"
                else :
                    print ke, "should a column name in your time sheet"
            except AssertionError:
                print record['pseudo'], "has an activity both in your sheet and in the key/pseudo table"
            except Exception as wtf:
                print "Something is wrong"
                print wtf


    if len(activities) > 0 :
        for k,a in activities.iteritems():
            try :
                a.save()
                time_sheet[k]['uploaded'] = "TRUE"
                print "Task", k, "uploaded"
            except Exception as wtf:
                print "Task", k, "failed to upload"
                print wtf


        shutil.copy(time_sheet_file,time_sheet_file + ".old")
        header_line = [ "\t".join(["ID"] + head)+"\n" ]
        data_lines = ["\t".join([str(k)] + [time_sheet[str(k)][h] for h in head] ) +"\n"  for k  in sorted([int(k) for k in time_sheet.keys()])]
        with open(time_sheet_file,"w") as handle:
            handle.writelines(header_line + data_lines)

        print "old time_sheet saved to",time_sheet_file + ".old", "new one to",  time_sheet_file

    else:
        print "No time entries added/update"

        
if __name__ == "__main__":
   main(sys.argv[1:])
