import React, {useState} from 'react';
import Box from "@mui/material/Box";
import axios from "axios";
import {useQuery} from "@tanstack/react-query";
import {error_log_viz_url, task_table_url} from "@jobmon_gui/configs/ApiUrls";
import {jobmonAxiosConfig} from "@jobmon_gui/configs/Axios";
import Typography from "@mui/material/Typography";
import {CircularProgress, Grid} from "@mui/material";
import {MaterialReactTable} from "material-react-table";
import {Button} from '@mui/material';
import {JobmonModal} from "@jobmon_gui/components/JobmonModal";
import ScrollableTextArea from "@jobmon_gui/components/ScrollableTextArea";
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import IconButton from "@mui/material/IconButton";

type ClusteredErrorsProps = {
    taskTemplateId: string | number
    workflowId: number | string
}

type ErrorSampleModalDetails = {
    sample_index: number
    sample_ids: number[]
}
export default function ClusteredErrors({taskTemplateId, workflowId}: ClusteredErrorsProps) {

    const [errorDetailIndex, setErrorDetailIndex] = useState<boolean | ErrorSampleModalDetails>(false)
    const errors = useQuery({
        queryKey: ["workflow_details", "clustered_errors", workflowId, taskTemplateId],
        queryFn: async () => {
            return axios.get(
                `${error_log_viz_url}${workflowId}/${taskTemplateId}#`,
                {
                    ...jobmonAxiosConfig,
                    data: null,
                    params: {cluster_errors: "true"}
                }
            ).then((r) => {
                return r.data
            })
        },
        enabled: !!taskTemplateId
    })

    const errorDetails = useQuery({
        queryKey: ["workflow_details", "error_details", workflowId, taskTemplateId, errorDetailIndex],
        queryFn: async () => {
            if (errorDetailIndex === false || errorDetailIndex === true) {
                return;
            }
            console.log("errorDetailIndex")
            console.log(errorDetailIndex)
            const ti_id = errorDetailIndex.sample_ids[errorDetailIndex.sample_index]
            return axios.get(
                `${error_log_viz_url}${workflowId}/${taskTemplateId}/${ti_id}`,
                {
                    ...jobmonAxiosConfig,
                    data: null,
                }
            ).then((r) => {
                console.log('r.data')
                console.log(r.data)
                return r.data
            })
        },
        enabled: !!taskTemplateId && errorDetailIndex !== false && errorDetailIndex !== true
    })


    if (!taskTemplateId) {
        return (<Typography sx={{pt: 5}}>Select a task template from above to clustered errors</Typography>)
    }
    if (errors.isLoading) {
        return (<CircularProgress/>)
    }
    if (errors.isError) {
        return (<Typography>Unable to retrieve clustered errors. Please refresh and try again</Typography>)
    }

    const columns = [
        {
            header: "Sample Error",
            accessorKey: "sample_error",
            Cell: ({renderedCellValue, row}) => (
                <Button sx={{textTransform: 'none', textAlign: "left"}}
                        onClick={() => setErrorDetailIndex({
                            sample_index: 0,
                            sample_ids: row.original.task_instance_ids
                        })}>
                    {renderedCellValue}
                </Button>
            ),
        },
        {
            header: "First Seen",
            accessorKey: "first_error_time",
        },
        {
            header: "Occurrences",
            accessorKey: "group_instance_count",
            desc: true,
        },
    ];

    const nextSample = () => {
        if (errorDetailIndex === false || errorDetailIndex === true ) {
            return;
        }
        setErrorDetailIndex({
            ...errorDetailIndex,
            sample_index: errorDetailIndex.sample_index + 1
        })
    }
    const previousSample = () => {
        if (errorDetailIndex === false || errorDetailIndex === true || errorDetailIndex.sample_index == 0) {
            return;
        }
        setErrorDetailIndex({
            ...errorDetailIndex,
            sample_index: errorDetailIndex.sample_index - 1
        })
    }
    const modalChildren = () => {
        if (errorDetails.isLoading) {
            return (<CircularProgress/>)
        }
        const error = errorDetails?.data?.error_logs[0] || false
        if (errorDetails.isError || !error) {
            return (<Typography>Failed to retrieve error details. Please refresh and try again</Typography>)
        }

        const labelStyles = {
            fontWeight: "bold",
        }

        return (<Box>
            <Box>
            <Typography sx={labelStyles}>Error Sample:
                <IconButton onClick={previousSample} disabled={errorDetailIndex?.sample_index == 0}><NavigateBeforeIcon/></IconButton> {errorDetailIndex?.sample_index+1} of {errorDetailIndex?.sample_ids?.length}
            <IconButton onClick={nextSample} disabled={errorDetailIndex?.sample_index == errorDetailIndex?.sample_ids?.length-1}><NavigateNextIcon/></IconButton>
            </Typography>
                </Box>
            <Grid container spacing={2}>
                <Grid item xs={3}><Typography sx={labelStyles}>Error Time:</Typography></Grid>
                <Grid item xs={9}>{error.error_time}</Grid>

                <Grid item xs={3}><Typography sx={labelStyles}>task_id:</Typography></Grid>
                <Grid item xs={9}>{error.task_id}</Grid>

                <Grid item xs={3}><Typography sx={labelStyles}>Task Instance Error ID:</Typography></Grid>
                <Grid item xs={9}>{error.task_instance_err_id}</Grid>

                <Grid item xs={3}><Typography sx={labelStyles}>workflow_id:</Typography></Grid>
                <Grid item xs={9}>{error.workflow_id}</Grid>

                <Grid item xs={3}><Typography sx={labelStyles}>workflow_run_id:</Typography></Grid>
                <Grid item xs={9}>{error.workflow_run_id}</Grid>

                <Grid item xs={12}><Typography sx={labelStyles}>Error Message:</Typography></Grid>
                <Grid item xs={12}><ScrollableTextArea sx={{backgroundColor:"#ccc", pl:2, pr: 2, pt: 2, pb:2}}>{error.error}</ScrollableTextArea></Grid>

                <Grid item xs={12}><Typography sx={labelStyles}>task_instance_stderr_log:</Typography></Grid>
                <Grid item xs={12}><ScrollableTextArea sx={{backgroundColor:"#ccc", pl:2, pr: 2, pt: 2, pb:2}}>{error.task_instance_stderr_log}</ScrollableTextArea></Grid>
            </Grid>
        </Box>)
    }

    const currentTiID = () => {
        if (errorDetailIndex === false || errorDetailIndex === true) {
            return ""
        }
        return errorDetailIndex?.sample_ids[errorDetailIndex?.sample_index]
    }


    return (
        <Box p={2} display="flex" justifyContent="center" width="100%">
            <MaterialReactTable columns={columns}
                                data={errors?.data.error_logs}/>
            <JobmonModal
                title={`Error Sample for Task Instance ID: ${currentTiID()}`}
                open={errorDetailIndex !== false}
                onClose={() => setErrorDetailIndex(false)} children={modalChildren()}/>

        </Box>
    )
}