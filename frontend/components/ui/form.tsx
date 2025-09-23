import * as React from "react";
import * as LabelPrimitive from "@radix-ui/react-label";
import { Slot } from "@radix-ui/react-slot";
import {
  Controller,
  type ControllerProps,
  type FieldPath,
  type FieldValues,
  FormProvider,
  useFormContext,
} from "react-hook-form";

import { cn } from "@/lib/utils";

const Form = FormProvider;

interface FormFieldContextValue<TFieldValues extends FieldValues = FieldValues, TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>> {
  name: TName;
}

const FormFieldContext = React.createContext<FormFieldContextValue | undefined>(undefined);

const FormItemContext = React.createContext<{ id: string } | undefined>(undefined);

const useFormFieldContext = () => {
  const fieldContext = React.useContext(FormFieldContext);
  if (!fieldContext) {
    throw new Error("FormFieldContext is missing. FormField must be used within a Form.");
  }
  const itemContext = React.useContext(FormItemContext);
  if (!itemContext) {
    throw new Error("FormItemContext is missing. FormItem must be used within a FormField.");
  }

  const { getFieldState, formState } = useFormContext();
  const fieldState = getFieldState(fieldContext.name, formState);

  const { id } = itemContext;

  const formItemId = id;
  const formDescriptionId = `${id}-description`;
  const formMessageId = `${id}-message`;

  return {
    id,
    name: fieldContext.name,
    formItemId,
    formDescriptionId,
    formMessageId,
    fieldState,
  };
};

const FormField = <TFieldValues extends FieldValues, TName extends FieldPath<TFieldValues>>({
  ...props
}: ControllerProps<TFieldValues, TName>) => (
  <FormFieldContext.Provider value={{ name: props.name }}>
    <Controller {...props} />
  </FormFieldContext.Provider>
);

const FormItem = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => {
    const id = React.useId();

    return (
      <FormItemContext.Provider value={{ id }}>
        <div ref={ref} className={cn("space-y-2", className)} {...props} />
      </FormItemContext.Provider>
    );
  },
);
FormItem.displayName = "FormItem";

const FormLabel = React.forwardRef<HTMLLabelElement, React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root>>(
  ({ className, ...props }, ref) => {
    const { formItemId, fieldState } = useFormFieldContext();

    return (
      <LabelPrimitive.Root
        ref={ref}
        className={cn(fieldState.invalid && "text-destructive", className)}
        htmlFor={formItemId}
        {...props}
      />
    );
  },
);
FormLabel.displayName = "FormLabel";

const FormControl = React.forwardRef<
  React.ElementRef<typeof Slot>,
  React.ComponentPropsWithoutRef<typeof Slot>
>(({ className, ...props }, ref) => {
  const { formItemId, formDescriptionId, formMessageId, fieldState } = useFormFieldContext();

  return (
    <Slot
      ref={ref}
      id={formItemId}
      aria-describedby={
        [props["aria-describedby"], formDescriptionId, formMessageId]
          .filter(Boolean)
          .join(" ") || undefined
      }
      aria-invalid={fieldState.invalid || undefined}
      className={className}
      {...props}
    />
  );
});
FormControl.displayName = "FormControl";

const FormDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => {
    const { formDescriptionId } = useFormFieldContext();

    return (
      <p
        ref={ref}
        id={formDescriptionId}
        className={cn("text-sm text-muted-foreground", className)}
        {...props}
      />
    );
  },
);
FormDescription.displayName = "FormDescription";

const FormMessage = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, children, ...props }, ref) => {
    const { fieldState, formMessageId } = useFormFieldContext();
    const body = fieldState.error ? children ?? fieldState.error.message : null;

    if (!body) {
      return null;
    }

    return (
      <p
        ref={ref}
        id={formMessageId}
        className={cn("text-sm text-destructive", className)}
        role="alert"
        aria-live="assertive"
        {...props}
      >
        {body}
      </p>
    );
  },
);
FormMessage.displayName = "FormMessage";

const useFormField = () => useFormFieldContext();

export { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage, useFormField };
